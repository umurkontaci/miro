from datetime import datetime
import os
import tempfile
import unittest
from glob import glob
import time

from miro import app
from miro import database
from miro import databaseupgrade
from miro import item
from miro import feed
from miro import schema
import shutil
from miro import storedatabase
from miro.plat import resources

from miro.test.framework import MiroTestCase, EventLoopTest
# sooo much easier to type...
from miro.schema import SchemaString, SchemaInt, SchemaFloat, SchemaReprContainer
from miro.schema import SchemaList, SchemaDict, SchemaObject, SchemaBool
from miro.schema import SchemaFilename, SchemaBinary

# create a dummy object schema
class Human(database.DDBObject):
    def setup_new(self, name, age, meters_tall, friends, high_scores=None,
            **stuff):
        self.name = name
        self.age = age
        self.meters_tall = meters_tall
        self.friends = friends
        self.friend_names = [f.name for f in friends]
        if high_scores is None:
            self.high_scores = {}
        else:
            self.high_scores = high_scores
        self.stuff = stuff
        self.id_code = None

    def add_friend(self, friend):
        self.friends.append(friend)
        self.friend_names.append(friend.name)

class RestorableHuman(Human):
    def setup_restored(self):
        self.iveBeenRestored = True

class PCFProgramer(Human):
    def setup_new(self, name, age, meters_tall, friends, file, developer,
            high_scores = None):
        Human.setup_new(self, name, age, meters_tall, friends, high_scores)
        self.file = file
        self.developer = developer

class SpecialProgrammer(PCFProgramer):
    def setup_new(self):
        PCFProgramer.setup_new(self, u'I.M. Special', 44, 2.1, [],
                '/home/specialdude/\u1234'.encode("utf-8"), True)

class HumanSchema(schema.ObjectSchema):
    klass = Human
    table_name = 'human'
    fields = [
        ('id', SchemaInt()),
        ('name', SchemaString()),
        ('age', SchemaInt()),
        ('meters_tall', SchemaFloat()),
        ('friend_names', SchemaList(SchemaString())),
        ('high_scores', SchemaDict(SchemaString(), SchemaInt())),
        ('stuff', SchemaReprContainer(noneOk=True)),
        ('id_code', SchemaBinary(noneOk=True)),
    ]

class RestorableHumanSchema(HumanSchema):
    klass = RestorableHuman
    table_name = 'restorable_human'

class PCFProgramerSchema(schema.MultiClassObjectSchema):

    table_name = 'pcf_programmer'
    fields = HumanSchema.fields + [
        ('file', SchemaFilename()),
        ('developer', SchemaBool()),
    ]

    @classmethod
    def ddb_object_classes(cls):
        return (PCFProgramer, SpecialProgrammer)

    @classmethod
    def get_ddb_class(cls, restored_data):
        if restored_data['name'] == 'I.M. Special':
            return SpecialProgrammer
        else:
            return PCFProgramer

test_object_schemas = [HumanSchema, PCFProgramerSchema, RestorableHumanSchema]

def upgrade1(cursor):
    cursor.execute("UPDATE human set name='new name'")

def upgrade2(cursor):
    1/0

class StoreDatabaseTest(EventLoopTest):
    OBJECT_SCHEMAS = None

    def setUp(self):
        EventLoopTest.setUp(self)
        self.save_path = tempfile.mktemp()
        self.remove_database()
        self.reload_test_database()

    def reload_test_database(self, version=0):
        self.reload_database(self.save_path, schema_version=version,
                object_schemas=self.OBJECT_SCHEMAS)

    def remove_database(self):
        try:
            os.unlink(self.save_path)
        except OSError:
            pass

    def tearDown(self):
        self.remove_database()
        corrupt_path = os.path.join(os.path.dirname(self.save_path),
                'corrupt_database')
        if os.path.exists(corrupt_path):
            os.remove(corrupt_path)
        databaseupgrade._upgrade_overide = {}
        EventLoopTest.tearDown(self)

class EmptyDBTest(StoreDatabaseTest):
    def test_open_empty_db(self):
        self.reload_test_database()
        app.db.cursor.execute("SELECT name FROM sqlite_master "
                "WHERE type='table'")
        for row in app.db.cursor.fetchall():
            table = row[0]
            if table == 'dtv_variables':
                correct_count = 1
            else:
                correct_count = 0
            app.db.cursor.execute("SELECT count(*) FROM %s" % table)
            self.assertEquals(app.db.cursor.fetchone()[0], correct_count)

class DBUpgradeTest(StoreDatabaseTest):
    def setUp(self):
        StoreDatabaseTest.setUp(self)
        self.save_path2 = tempfile.mktemp()

    def tearDown(self):
        try:
            os.unlink(self.save_path2)
        except:
            pass
        StoreDatabaseTest.tearDown(self)

    def test_indexes_same(self):
        self.remove_database()
        self.reload_database()
        app.db.cursor.execute("SELECT name FROM sqlite_master "
                "WHERE type='index'")
        blank_db_indexes = set(app.db.cursor)
        shutil.copy(resources.path("testdata/olddatabase.v79"),
                self.save_path2)
        self.reload_database(self.save_path2)
        app.db.cursor.execute("SELECT name FROM sqlite_master "
                "WHERE type='index'")
        upgraded_db_indexes = set(app.db.cursor)
        self.assertEquals(upgraded_db_indexes, blank_db_indexes)

    def test_schema_same(self):
        self.remove_database()
        self.reload_database()
        blank_column_types = self._get_column_types()
        shutil.copy(resources.path("testdata/olddatabase.v79"),
                self.save_path2)
        self.reload_database(self.save_path2)
        upgraded_column_types = self._get_column_types()
        self.assertEquals(set(blank_column_types.keys()),
                set(upgraded_column_types.keys()))
        for table_name in blank_column_types:
            diff = blank_column_types[table_name].symmetric_difference(
                    upgraded_column_types[table_name])
            if diff:
                raise AssertionError("different column types for %s (%s)" %
                        (table_name, diff))

    def _get_column_types(self):
        app.db.cursor.execute("SELECT name FROM sqlite_master "
                "WHERE type='table'")
        rv = {}
        for table_name in app.db.cursor.fetchall():
            app.db.cursor.execute('pragma table_info(%s)' % table_name)
            rv[table_name] = set((r[1], r[2].lower()) for r in app.db.cursor)
        return rv

class FakeSchemaTest(StoreDatabaseTest):
    OBJECT_SCHEMAS = test_object_schemas

    def setUp(self):
        StoreDatabaseTest.setUp(self)
        self.lee = Human(u"lee", 25, 1.4, [], {u'virtual bowling': 212})
        self.joe = RestorableHuman(u"joe", 14, 1.4, [self.lee], car=u'toyota',
                dog=u'scruffy')
        self.ben = PCFProgramer(u'ben', 25, 3.4, [self.joe],
                '/home/ben/\u1234'.encode("utf-8"), True)
        self.db = [ self.lee, self.joe, self.ben]
        databaseupgrade._upgrade_overide[1] = upgrade1
        databaseupgrade._upgrade_overide[2] = upgrade2

class DiskTest(FakeSchemaTest):
    def check_database(self):
        obj_map = {}
        for klass in (PCFProgramer, RestorableHuman, Human):
            obj_map.update(dict((obj.id, obj) for obj in klass.make_view()))
        self.assertEquals(len(self.db), len(obj_map))
        for obj in self.db:
            if isinstance(obj, PCFProgramer):
                schema = PCFProgramerSchema
            elif isinstance(obj, RestorableHuman):
                schema = RestorableHumanSchema
            elif isinstance(obj, Human):
                schema = HumanSchema
            else:
                raise AssertionError("Unknown object type: %r" % obj)

            db_object = obj_map[obj.id]
            self.assertEquals(db_object.__class__, obj.__class__)
            for name, schema_item in schema.fields:
                db_value = getattr(db_object, name)
                obj_value = getattr(obj, name)
                if db_value != obj_value or type(db_value) != type(obj_value):
                    raise AssertionError("%r != %r (attr: %s)" % (db_value,
                        obj_value, name))

    def test_create(self):
        # Test that the database we set up in __init__ restores correctly
        self.reload_test_database()
        self.check_database()

    def test_update(self):
        self.joe.name = u'JO MAMA'
        self.joe.signal_change()
        self.reload_test_database()
        self.check_database()

    def test_binary_reload(self):
        self.joe.id_code = 'abc'
        self.joe.signal_change()
        self.reload_test_database()
        self.check_database()

    def test_remove(self):
        self.joe.remove()
        self.db = [ self.lee, self.ben]
        self.reload_test_database()
        self.check_database()

    def test_update_then_remove(self):
        self.joe.name = u'JO MAMA'
        self.joe.remove()
        self.db = [ self.lee, self.ben]
        self.reload_test_database()
        self.check_database()

    def test_schema_repr(self):
        self.joe.stuff = {
                '1234': datetime.now(),
                None: time.localtime(),
                u'booya': 23.0
                }
        self.joe.signal_change()
        self.reload_test_database()
        self.check_database()

    def test_setup_restored(self):
        self.assert_(not hasattr(self.joe, 'iveBeenRestored'))
        self.reload_test_database()
        restored_joe = RestorableHuman.get_by_id(self.joe.id)
        self.assert_(restored_joe.iveBeenRestored)

    def test_single_table_inheritance(self):
        # test loading different classes based on the row data
        im_special = SpecialProgrammer()
        self.db.append(im_special)
        self.reload_test_database()
        self.check_database()
        # check deleting the different class
        im_special.remove()
        self.db.pop()
        self.reload_test_database()
        self.check_database()

    def test_commit_without_close(self):
        # we should commit using an idle callback.
        self.runPendingIdles()
        # close the database connection without giving LiveStorage the
        # oppertunity to commit when it's closed.
        app.db.connection.close()
        app.db = storedatabase.LiveStorage(self.save_path,
                schema_version=0, object_schemas=self.OBJECT_SCHEMAS)
        app.db.upgrade_database()
        self.check_database()

    def test_upgrade(self):
        self.reload_test_database(version=1)
        new_lee = Human.get_by_id(self.lee.id)
        self.assertEquals(new_lee.name, 'new name')

    def test_restore_with_newer_version(self):
        self.reload_test_database(version=1)
        self.assertRaises(databaseupgrade.DatabaseTooNewError,
                self.reload_test_database, version=0)

    def test_last_id(self):
        correct_last_id = database.DDBObject.lastID
        database.DDBObject.lastID = 0
        self.reload_test_database()
        self.assert_(database.DDBObject.lastID > 0)
        self.assertEquals(database.DDBObject.lastID, correct_last_id)

    def check_reload_error(self, **reload_args):
        corrupt_path = os.path.join(os.path.dirname(self.save_path),
                'corrupt_database')
        self.assert_(not os.path.exists(corrupt_path))
        self.reload_test_database(**reload_args)
        self.assert_(os.path.exists(corrupt_path))

    def test_upgrade_error(self):
        self.check_reload_error(version=2)

    def test_corrupt_database(self):
        app.db.close()
        open(self.save_path, 'wb').write("BOGUS DATA")
        self.check_reload_error()

    def test_database_data_error(self):
        app.db.cursor.execute("DROP TABLE human")
        self.check_reload_error()

class ObjectMemoryTest(FakeSchemaTest):
    def test_remove_remove_object_map(self):
        self.reload_test_database()
        # no objects should be loaded yet
        self.assertEquals(0, len(app.db._object_map))
        # test object loading
        lee = Human.make_view().get_singleton()
        self.assertEquals(1, len(app.db._object_map))
        joe = RestorableHuman.make_view().get_singleton()
        self.assertEquals(2, len(app.db._object_map))
        # test object removal
        joe.remove()
        self.assertEquals(1, len(app.db._object_map))
        lee.remove()
        self.assertEquals(0, len(app.db._object_map))

class ValidationTest(FakeSchemaTest):
    def assert_object_valid(self, obj):
        obj.signal_change()

    def assert_object_invalid(self, obj):
        self.assertRaises(schema.ValidationError, obj.signal_change)

    def testNoneValues(self):
        self.lee.age = None
        self.assert_object_invalid(self.lee)
        self.lee.age = 25
        self.lee.stuff = None
        self.assert_object_valid(self.lee)

    def testIntValidation(self):
        self.lee.age = '25'
        self.assert_object_invalid(self.lee)
        self.lee.age = 25L
        self.assert_object_valid(self.lee)

    def testStringValidation(self):
        self.lee.name = 133
        self.assert_object_invalid(self.lee)
        self.lee.name = u'lee'
        self.assert_object_valid(self.lee)

    def testBinaryValidation(self):
        self.lee.id_code = u'abc'
        self.assert_object_invalid(self.lee)
        self.lee.id_code = 'abc'
        self.assert_object_valid(self.lee)

    def testFloatValidation(self):
        self.lee.meters_tall = 3
        self.assert_object_invalid(self.lee)

    def testListValidation(self):
        self.lee.friend_names = [1234]
        self.assert_object_invalid(self.lee)

    def testDictValidation(self):
        self.joe.high_scores['pong'] = u"One Million"
        self.assert_object_invalid(self.joe)
        del self.joe.high_scores['pong']
        self.joe.high_scores[1943] = 1234123
        self.assert_object_invalid(self.joe)

if __name__ == '__main__':
    unittest.main()
