#!/usr/bin/env python3
"""Synthetic listing-input negatives ONLY; real server is verified separately."""
import copy
import unittest
from qa import mcp_http_selftest as gate

OLD = {'error_tail','diag_read','version_info','fs_read'}
NEW = {'sync_connect','sync_disconnect','start_import','start_publish','abort','courses_read','courses_write','pickup_import','devices_list','pairing_state','sync_state'}
READ = OLD | {'courses_read','pairing_state','sync_state'}

def listing(names):
    return [{'name':name,'inputSchema':{'type':'object','required':[],'additionalProperties':False},
             'annotations':{'readOnlyHint':name in READ}} for name in sorted(names)]

class Mcp029ListingTest(unittest.TestCase):
    def test_exact_host_four_and_release_fifteen(self):
        self.assertEqual(OLD, gate.expected_tool_names(True))
        self.assertEqual(OLD|NEW,gate.expected_tool_names(False))
        self.assertTrue(gate.valid_tool_listing(listing(OLD),True))
        self.assertTrue(gate.valid_tool_listing(listing(OLD|NEW),False))
    def test_count_names_duplicates_and_extra_never_relaxed(self):
        good=listing(OLD|NEW)
        for mutated in [good[:-1],good+[good[0]],listing(OLD),listing((OLD|NEW)-{'abort'}|{'surprise'})]:
            self.assertFalse(gate.valid_tool_listing(mutated,False))
        self.assertFalse(gate.valid_tool_listing(good,True))
    def test_original_and_new_schema_annotations_still_exact(self):
        good=listing(OLD|NEW)
        for index in range(len(good)):
            for key,value in [('readOnlyHint',not good[index]['annotations']['readOnlyHint'])]:
                mutated=copy.deepcopy(good);mutated[index]['annotations'][key]=value
                self.assertFalse(gate.valid_tool_listing(mutated,False))
            for key,value in [('type','array'),('additionalProperties',True),('required',None)]:
                mutated=copy.deepcopy(good);mutated[index]['inputSchema'][key]=value
                self.assertFalse(gate.valid_tool_listing(mutated,False))

if __name__=='__main__': unittest.main(verbosity=2)
