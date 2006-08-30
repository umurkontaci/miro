import unittest
import resource
import os
import re
import time
import copy
import feedparser
import feed
import item
import app
import maps

from template import *
from time import time
import database
import gettext
import compiled_templates

from test.framework import DemocracyTestCase

ranOnUnload = 0

HTMLPattern = re.compile("^.*<body.*?>(.*)</body\s*>", re.S)

class HTMLObject(database.DDBObject):
    def __init__(self,html):
        self.html = html
        database.DDBObject.__init__(self)

class DOMTracker:
    def __init__(self):
        self.callList = []
    def addItemAtEnd(self, xml, id):
        self.callList.append({'name':'addItemAtEnd','xml':xml,'id':id})
    def addItemBefore(self, xml, id):
        self.callList.append({'name':'addItemBefore','xml':xml,'id':id})
    def removeItem(self, id):
        self.callList.append({'name':'removeItem','id':id})
    def removeItems(self, ids):
        self.callList.append({'name':'removeItems','ids':ids})
    def changeItem(self, id, xml):
        self.callList.append({'name':'changeItem','xml':xml,'id':id})
    def changeItems(self, pairs):
        self.callList.append({'name':'changeItems','pairs':pairs})
    def hideItem(self, id):
        self.callList.append({'name':'hideItem','id':id})
    def showItem(self, id):
        self.callList.append({'name':'showItem','id':id})

class ChangeDelayedDOMTracker(DOMTracker):
    def changeItem(self, id, xml):
        time.sleep(0.1)
        self.callList.append({'name':'changeItem','xml':xml,'id':id})

class SimpleTest(DemocracyTestCase):
    def setUp(self):
        handle = file(resource.path("templates/unittest/simple"),"r")
        self.text = handle.read()
        handle.close()
        self.text = HTMLPattern.match(self.text).group(1)
    def test(self):
        (tch, handle) = fillTemplate("unittest/simple",DOMTracker(),'gtk-x11-MozillaBrowser','platform')
        text = tch.read()
        text = HTMLPattern.match(text).group(1)
        self.assertEqual(text,self.text)

class TranslationTest(DemocracyTestCase):
    def setUp(self):
        handle = file(resource.path("testdata/translation-result"),"r")
        self.text = handle.read()
        handle.close()
        self.text = HTMLPattern.match(self.text).group(1)
        self.oldgettext = gettext.gettext
    def tearDown(self):
        compiled_templates.unittest.translationtest._ = self.oldgettext
        DemocracyTestCase.tearDown(self)
    def test(self):
        compiled_templates.unittest.translationtest._ = lambda x : '!%s!' % x
        (tch, handle) = fillTemplate("unittest/translationtest",DOMTracker(),'gtk-x11-MozillaBrowser','platform')
        compiled_templates.unittest.translationtest._ = self.oldgettext
        text = tch.read()
        text = HTMLPattern.match(text).group(1)
        self.assertEqual(text,self.text)

class ReplaceTest(DemocracyTestCase):
    def setUp(self):
        handle = file(resource.path("testdata/replace-result"),"r")
        self.text = handle.read()
        handle.close()
        self.text = HTMLPattern.match(self.text).group(1)
    def test(self):
        (tch, handle) = fillTemplate("unittest/replace",DOMTracker(),'gtk-x11-MozillaBrowser','platform')
        text = tch.read()
        text = HTMLPattern.match(text).group(1)
        self.assertEqual(text,self.text)

class HideTest(DemocracyTestCase):
    def setUp(self):
        DemocracyTestCase.setUp(self)
        handle = file(resource.path("testdata/hide-result"),"r")
        self.text = handle.read()
        handle.close()
        self.text = HTMLPattern.match(self.text).group(1)
    def test(self):
        (tch, handle) = fillTemplate("unittest/hide",DOMTracker(),'gtk-x11-MozillaBrowser','platform')
        text = tch.read()
        text = HTMLPattern.match(text).group(1)
        self.assertEqual(text,self.text)

class ViewTest(DemocracyTestCase):
    pattern = re.compile("^\n<h1>view test template</h1>\n<span id=\"([^\"]+)\"/>\n", re.S)
    doublePattern = re.compile("^\n<h1>view test template</h1>\n<span id=\"([^\"]+)\"/>\n<span id=\"([^\"]+)\"/>\n", re.S)
    updatePattern = re.compile("^\n<h1>update test template</h1>\n<span id=\"([^\"]+)\"/>\n", re.S)
    hidePattern = re.compile("^\n<h1>update hide test template</h1>\n<div class=\"foo\" id=\"([^\"]+)\"", re.S)
    itemPattern = re.compile("<div id=\"(.*?)\">\n<span>testview\d*</span>\n<span>&lt;span&gt;object&lt;/span&gt;</span>\n<span><span>object</span></span>\n\n<div>\nhideIf:False\n<span>This is an include</span>\n\n<span>This is a template include</span>\n\n<span>&lt;span&gt;This is a database replace&lt;/span&gt;</span>\n<span><span>This is a database replace</span></span>\n</div>\n</div>",re.S)

    def setUp(self):
        global ranOnUnload
        ranOnUnload = 0
        DemocracyTestCase.setUp(self)
        self.everything = database.defaultDatabase
        self.x = HTMLObject('<span>object</span>')
        self.y = HTMLObject('<span>object</span>')
        self.domHandle = DOMTracker()

    def test(self):
        (tch, handle) = fillTemplate("unittest/view",self.domHandle,'gtk-x11-MozillaBrowser','platform')
        text = tch.read()
        text = HTMLPattern.match(text).group(1)
        self.assert_(self.pattern.match(text)) #span for template inserted
        id = self.pattern.match(text).group(1)
        handle.initialFillIn()
        self.assertEqual(len(self.domHandle.callList),1)
        self.assertEqual(self.domHandle.callList[0]['name'],'addItemBefore')
        self.assertEqual(self.domHandle.callList[0]['id'],id)
        match = self.itemPattern.findall(self.domHandle.callList[0]['xml'])
        self.assertEqual(len(match),2)
        self.assertNotEqual(match[0], match[1])
        self.assertEqual(ranOnUnload, 0)
        handle.unlinkTemplate()
        self.assertEqual(ranOnUnload, 1)

    def testUpdate(self):
        (tch, handle) = fillTemplate("unittest/update",self.domHandle,'gtk-x11-MozillaBrowser','platform')
        text = tch.read()
        text = HTMLPattern.match(text).group(1)
        self.assert_(self.updatePattern.match(text)) #span for template inserted
        id = self.updatePattern.match(text).group(1)
        handle.initialFillIn()
        self.assertEqual(len(self.domHandle.callList),1)
        self.assertEqual(self.domHandle.callList[0]['name'],'addItemBefore')
        self.assertEqual(self.domHandle.callList[0]['id'],id)
        match = self.itemPattern.findall(self.domHandle.callList[0]['xml'])
        self.assertEqual(len(match),1)
        self.x.signalChange()
        handle.updateRegions[0].doChange()
        self.assertEqual(len(self.domHandle.callList),2)
        self.assertEqual(self.domHandle.callList[1]['name'],'changeItem')
        self.assertEqual(self.domHandle.callList[1]['id'],match[0])
        temp = HTMLObject('<span>object</span>')
        handle.updateRegions[0].doChange()
        self.assertEqual(len(self.domHandle.callList),3)
        self.assertEqual(self.domHandle.callList[2]['name'],'changeItem')
        self.assertEqual(self.domHandle.callList[2]['id'],match[0])
        temp.remove()
        handle.updateRegions[0].doChange()
        self.assertEqual(len(self.domHandle.callList),4)
        self.assertEqual(self.domHandle.callList[3]['name'],'changeItem')
        self.assertEqual(self.domHandle.callList[3]['id'],match[0])
        self.assertEqual(ranOnUnload, 0)
        handle.unlinkTemplate()
        self.assertEqual(ranOnUnload, 1)

    def testHide(self):
        (tch, handle) = fillTemplate("unittest/update-hide",self.domHandle,'gtk-x11-MozillaBrowser','platform')
        text = tch.read()
        text = HTMLPattern.match(text).group(1)
        self.assert_(self.hidePattern.match(text)) #span for template inserted
        id = self.hidePattern.match(text).group(1)
        handle.initialFillIn()
        self.assertEqual(len(self.domHandle.callList),0)
        self.x.signalChange()
        self.assertEqual(len(self.domHandle.callList),0)
        temp = HTMLObject('<span>object</span>')
        self.assertEqual(len(self.domHandle.callList),1)
        self.assertEqual(self.domHandle.callList[0]['name'],'showItem')
        self.assertEqual(self.domHandle.callList[0]['id'],id)
        temp.remove()
        self.assertEqual(len(self.domHandle.callList),2)
        self.assertEqual(self.domHandle.callList[1]['name'],'hideItem')
        self.assertEqual(self.domHandle.callList[1]['id'],id)
        self.assertEqual(ranOnUnload, 0)
        handle.unlinkTemplate()
        self.assertEqual(ranOnUnload, 1)

    def testTwoViews(self):
        (tch, handle) = fillTemplate("unittest/view-double",self.domHandle,'gtk-x11-MozillaBrowser','platform')
        text = tch.read()
        text = HTMLPattern.match(text).group(1)
        assert(self.doublePattern.match(text)) #span for template inserted
        id = self.doublePattern.match(text).group(1)
        id2 = self.doublePattern.match(text).group(2)
        handle.initialFillIn()
        self.assertEqual(len(self.domHandle.callList),2)
        self.assertEqual(self.domHandle.callList[0]['name'],'addItemBefore')
        self.assertEqual(self.domHandle.callList[1]['name'],'addItemBefore')
        self.assert_(self.domHandle.callList[0]['id'] != self.domHandle.callList[1]['id'])
        self.assert_(self.domHandle.callList[0]['id'] in [id, id2])
        self.assert_(self.domHandle.callList[1]['id'] in [id, id2])
        items1 = self.itemPattern.findall(self.domHandle.callList[0]['xml'])
        items2 = self.itemPattern.findall(self.domHandle.callList[1]['xml'])

        match = copy.copy(items1)
        match.extend(items2)
        self.assertEqual(len(match),4)

        self.x.signalChange()
        handle.trackedViews[0].callback()
        handle.trackedViews[1].callback()
        self.x.remove()
        handle.trackedViews[0].callback()
        handle.trackedViews[1].callback()
        self.assertEqual(len(self.domHandle.callList),6)
        self.assertEqual(self.domHandle.callList[2]['name'],'changeItems')
        self.assertEqual(self.domHandle.callList[3]['name'],'changeItems')
        self.assertEqual(self.domHandle.callList[4]['name'],'removeItems')
        self.assertEqual(self.domHandle.callList[5]['name'],'removeItems')
        changed1 = [p[0] for p in self.domHandle.callList[2]['pairs']]
        changed2 = [p[0] for p in self.domHandle.callList[3]['pairs']]
        self.assertEqual(len(changed1), 1)
        self.assertEqual(len(changed2), 1)
        self.assert_((changed1[0] in items1 and changed2[0] in items2) or
                changed1[0] in items2 and changed2[0] in items1)
        self.assertEqual(self.domHandle.callList[4]['name'],'removeItems')
        self.assertEqual(self.domHandle.callList[5]['name'],'removeItems')
        self.assertEquals(len(self.domHandle.callList[4]['ids']), 1)
        self.assertEquals(len(self.domHandle.callList[5]['ids']), 1)
        self.assert_(((self.domHandle.callList[4]['ids'][0] in items1) and
                          (self.domHandle.callList[5]['ids'][0] in items2)) or
                         ((self.domHandle.callList[4]['ids'][0] in items2) and
                          (self.domHandle.callList[5]['ids'][0] in items1)))

        self.x = HTMLObject('<span>object</span>')
        handle.trackedViews[0].callback()
        handle.trackedViews[1].callback()
        self.assertEqual(len(self.domHandle.callList),8)
        self.assertEqual(self.domHandle.callList[6]['name'],'addItemBefore')
        match.extend(self.itemPattern.findall(self.domHandle.callList[6]['xml']))
        self.assertEqual(self.domHandle.callList[7]['name'],'addItemBefore')
        match.extend(self.itemPattern.findall(self.domHandle.callList[7]['xml']))
        self.assertEqual(len(match),6)
        for x in range(len(match)):
            for y in range(x+1,len(match)):
                self.assertNotEqual(match[x],match[y])
        self.assertEqual(ranOnUnload, 0)
        handle.unlinkTemplate()
        self.assertEqual(ranOnUnload, 1)

class TemplatePerformance(DemocracyTestCase):
    def setUp(self):
        global ranOnUnload
        ranOnUnload = 0
        DemocracyTestCase.setUp(self)
        self.everything = database.defaultDatabase
        self.domHandle = DOMTracker()

    def timeIt(self, func, repeat):
        start = time()
        for x in xrange(repeat):
            func()
        totalTime = time() - start
        return totalTime

    def testRender(self):
        self.feeds = []
        self.items = []
        for x in range(50):
            self.feeds.append(feed.Feed('http://www.getdemocracy.com/50'))
            for y in range(50):
                self.items.append(item.Item(feedparser.FeedParserDict(
                    {'title':"%d-%d" % (x,y),
                     'enclosures':[{'url': 'file://%d-%d.mpg' % (x,y)}]}),
                                            feed_id = self.feeds[-1].id
                                            ))
        
        time1 = self.timeIt(self.fillAndUnlink, 10)

        for x in range(50):
            for y in range(450):
                self.items.append(item.Item(feedparser.FeedParserDict(
                    {'title':"%d-%d" % (x,y),
                     'enclosures':[{'url': 'file://%d-%d.mpg' % (x,y)}]}),
                                       feed_id = self.feeds[x].id
                                       ))
        time2 = self.timeIt(self.fillAndUnlink, 10)

        # print "Filling in a 500 item feed took roughly %.4f secs" % (time2/10.0)
        # Check that filling in 500 items takes no more than roughly
        # 10x filling in 50 items
        self.assert_(time2/time1 < 11, 'Template filling does not scale linearly')


    def fillAndUnlink(self):
        (tch, handle) = fillTemplate("channel",self.domHandle,'gtk-x11-MozillaBrowser','platform', id=self.feeds[-1].getID())
        tch.read()
        handle.initialFillIn()
        handle.unlinkTemplate()
