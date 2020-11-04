# /usr/bin/python
# -*- coding: utf-8 -*-
import argparse, os
input_string = 'CT, Coronary Artery                                20161130 20161130 10:51    *  Good image quality.       1. Coronary artery disease : Increased calcified plaque volume, since 2011.     LM and pdLCX: minimal, discrete stenossi with calcified plaque.     OM: severe, discrete stenosis with calcified plaque.     pLAD and D1: moderate to severe, diffuse stenosis with calcified plaque.     pmdRCA: moderate to severe, diffuse stenosis with diffuse calcified(pdRCA) or non-calcified(mRCA) plaques.         <Stenosis degree>    Minimal: <30%, Mild: 30-49%, Moderate: 50-69%, Severe: >70%    2. Other coronary findings:    1) Right dominant coronary artery system.    2) Anatomy variation or anomaly of coronary artery: none.    3. Calcium scoring:    Agatston score: 1274.2 -> 2045.9    4. Other findings(lung) :   - Bronchiectasis, LLL.    -----------------------------------------------------------------------------  Guidelines for Calcium Score   -----------------------------------------------------------------------------  Calcium Plaque           Probability of          Coronary     Hazard Ratio  Score   Burden (†)      Significant CAD (†)    Event (‡)                                                      5-Year                                                    Incidence                         0 ----------------------------------------------------------------------  0          No identifi-     Very low,               0.5%            1.00          able plaque      generally < 5%                  1 ----------------------------------------------------------------------  1          Minimal          Very unlikely,           identifiable        < 10%           plaque burden                                   10 ----------------------------------------     4.6%      3.61 (1.96-6.65)          Definite, at    Mild or Minimal          least mild       coronary stenosis          atherosclerotic  likely          plaque burden   100 ------------------------------------------------------'

meaninglessness_phrase = set([
	'<Stenosis degree> Minimal: <30%, Mild: 30-49%, Moderate: 50-69%, Severe: >70%',
	'<Stenosis degree> Minimal: <30%, Mild: 30-49%, Moderate: 50-69%, Severe: > 70%',
	'<Degree of stenosis> Minimal: 0-29%, Mild: 30-49%, Moderate: 50-69%, Severe: 70-100%',
	'(minimal: <30%, mild: 30-49%, moderate: 50-69%, severe: >70%)',
	'*Minimal: <30%, Mild: 30-49%, Moderate: 50-69%, Severe: >70% (diameter).',
	'Guidelines for Calcium Score',
	'0 No identifi- Very low, 0.5% 1.00 able plaque generally < 5% 1',
	'1 Minimal Very unlikely, identifiable < 10% plaque burden',
	'(LAP: low attenuated plaque, PR: positive remodel, SC: spotty calcium)',
	'(LAP: low attenuated plaque, PR: positive remodel, SC: spotty calcium, NRS: napkin-ring sign)',
	'*LAP: low attenuated plaque, PR: positive remodel, SC: spotty calcium.',
	'CAD = coronary artery disease',
	'Mayo Clin Proc 1999;74:243-252',
	'NEJM 2008;358:1336-1345',
	'Ref)',
	'Findings:'
	])

meaninglessness_sentence = set([

	])

enditem_token = set(['.  '])

headitem_token  = set(['  *  ', ' - ', 
                    '  1. ', '  2. ', '  3. ', '  4. ', '  5. ', 
                    '  1) ', '  2) ', '  3) ', '  4) ', '  5) ', 
					'Findings:', 'Findings :'])

bar_token = '-----'


def insert_newline(sentence, idx):
    if not sentence[:idx].endswith('\n') and idx != -1:
        sentence = sentence[:idx] + '\n' + sentence[idx:].strip()

    return sentence


def sentence_tokenize(sentences):
	del_sen_lists = []

	try:
		sentences = sentences.strip()
	except AttributeError:
		return []
	

	bar_begin_idx = 0
	bar_end_idx = 0
	for idx, char in enumerate(sentences):
		# print(idx, char)
		if char == '-' and bar_begin_idx == 0:
			bar_begin_idx = idx
			bar_end_idx = idx
		elif char == '-' :
			bar_end_idx = idx

		if bar_begin_idx !=0 and bar_end_idx !=0:
			if char != '-':
				# print bar_begin_idx,  bar_end_idx
				# print sentences[bar_begin_idx:bar_end_idx]
				if len(sentences[bar_begin_idx:bar_end_idx+1]) > 10:
					del_sen_lists.append(sentences[bar_begin_idx:bar_end_idx+1])
				bar_begin_idx = 0
				bar_end_idx = 0



	del_sen_lists.sort(key = lambda x:len(x), reverse=True)
	# print(del_sen_lists)
	for s in del_sen_lists:
		sentences = sentences.replace(s, '\n')

	for s in headitem_token:
		sentences = sentences.replace(s, '\n'+s.lstrip())

	for s in enditem_token:
		sentences = sentences.replace(s, s+'\n')

	sentence_list = sentences.split('\n')
	table_idx = -1
	for i, sen in enumerate(sentence_list):
		if "segment stenosis degree length plaque" in ' '.join(sen.lower().split()):
			table_idx = i+2
			break
	if table_idx != -1:
		sentence = []
		tokens = sentence_list[table_idx].split()
		del sentence_list[table_idx]
		for token in tokens:
			sentence.append(token)
			if token in ['mixed', 'calcified', 'non-calcified']:
				sentence_list.insert(table_idx, ' '.join(sentence))
				sentence = []

	return sentence_list


def remove_useless_sentence(input_list):
	for x in input_list:
		if len(x.strip()) < 1:
			input_list = list(filter(lambda a: a != x, input_list))

	# 부분 체크 
	for idx, x in enumerate(input_list):
		for p in meaninglessness_phrase:
			x = ' '.join(x.split())
			if p in x:
				x = x.replace(p, '')
				# print ("kekeeo:", x)
				input_list[idx] = x

	# 문장 전체 체크 
	for x in input_list:
		if x.lower().replace(' ','') in meaninglessness_sentence:
			input_list = list(filter(lambda a: a != x, input_list))
			
	
	for x in input_list:
		if len(x)>1 and len(x.replace('-','')) == 0:
			input_list = list(filter(lambda a: a != x, input_list))
		
	for x in input_list:
		if x.lower().replace(' ','').startswith('calciumplaqueprobabilityofcoronaryevent(') and x.lower().replace(' ','').endswith(')5-yearhazardratioincidence0'):
			input_list = list(filter(lambda a: a != x, input_list))

	# return input_list
	return squeeze(input_list)



def squeeze(input_list):
	return_list = []
	for x in input_list:
		return_list.append(' '.join(x.split()))
	print(return_list)
	return return_list


# sen_list = sentence_tokenize(input_string)
# for sen in sen_list:
# 	print(sen)
# for x in remove_useless_sentence(sen_list):
# 	print(x)

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("-input_dir", default="./input")
	parser.add_argument("-output_dir", default="./output")

	args = parser.parse_args()

	filenames = os.listdir(args.input_dir)
	for filename in filenames:
		with open(os.path.join(args.input_dir, filename), 'r', encoding='utf-8') as f:
			input_text = f.read()
		sen_list = sentence_tokenize(input_text)
		output = remove_useless_sentence(sen_list)

		with open(os.path.join(args.output_dir, filename), 'w', encoding='utf-8') as f:
			f.write('\n'.join(output))

