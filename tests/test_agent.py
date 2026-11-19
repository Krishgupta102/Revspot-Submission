import importlib.util, pathlib, unittest
p=pathlib.Path(__file__).parents[1]/'backend/server.py'
spec=importlib.util.spec_from_file_location('voice_server',p); app=importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
class FlowTests(unittest.TestCase):
 def test_full_qualified_investor_flow(self):
  lead={'language':'English'}
  turns=['Yes, now is fine.','Investment.','Nandi Hills is fine.','₹1.5 crore is comfortable.','December 2029 works.']
  replies=[app.generate_reply(lead,t) for t in turns]
  self.assertEqual(lead['intent'],'Investment'); self.assertEqual(lead['location_fit'],'Yes')
  self.assertEqual(lead['budget'],'Fit'); self.assertEqual(lead['timeline'],'Comfortable')
  self.assertIn('property expert',replies[-1].lower())
 def test_natural_location_acknowledgements_advance_flow(self):
  for answer in ['it works for me','good','The location works.']:
   lead={'language':'English','intent':'Investment'}
   reply=app.generate_reply(lead,answer)
   self.assertEqual(lead['location_fit'],'Yes')
   self.assertIn('92.4 lakh',reply.lower())
 def test_assessment_conversation_handles_short_answers_and_unclear_speech(self):
  lead={'language':'English'}
  self.assertIn('own use',app.generate_reply(lead,'Yes'))
  self.assertIn('Nandi Hills',app.generate_reply(lead,'A weekend home for my family.'))
  self.assertEqual(lead['intent'],'Self-use')
  reply=app.generate_reply(lead,'The location works.')
  self.assertEqual(lead['location_fit'],'Yes')
  self.assertIn('92.4 lakh',reply)
  reply=app.generate_reply(lead,'My budget is ₹75 lakh.')
  self.assertEqual(lead['budget'],'Below range')
  self.assertIn('timeline',reply.lower())
  reply=app.generate_reply(lead,'yeah good')
  self.assertEqual(lead['timeline'],'Comfortable')
  self.assertIn('property expert',reply.lower())
  reply=app.generate_reply(lead,'jvkfv')
  self.assertIn('did not catch that',reply.lower())
  self.assertIn('Property Expert',reply)
 def test_below_budget(self):
  result=app.classify('My budget is ₹75 lakh','English')
  self.assertEqual(result['budget'],'Below range')
 def test_location_mismatch_captured(self):
  self.assertEqual(app.classify('Devanahalli is too far for me','English')['location_fit'],'No')
 def test_busy_is_respected(self):
  self.assertIn('let you go',app.generate_reply({},'I am busy, call later').lower())
 def test_opt_out_ends_call(self):
  lead={}
  self.assertIn('end the call',app.generate_reply(lead,'Stop calling me').lower())
  self.assertTrue(lead['do_not_call'])
 def test_hindi_path(self):
  lead={'language':'Hindi'}
  self.assertIn('समझ गई',app.generate_reply(lead,'नमस्ते हिंदी में','English'))
if __name__=='__main__': unittest.main()
