import nltk
import collections
import json
import argparse, os


def process(string):
	finding_kb = set([])

	rlt_knowledge = {
		'date': set([]),
		'code': set([]),
		'lesion_segment': set([]),
		'lesion_highriskplq_flag': None
	}

	return_list_info = []
	return_list_triple = []
	return_txt = ''

	for row in string.split('\n'):
		row = row.strip()

		if row.startswith('[Finding]:'):
			rlt_knowledge['code'] = rlt_knowledge['code'] | detectCTcode(row)
			rlt_knowledge['date'] = rlt_knowledge['date'] | detectDate(row)

			finding_kb = finding_kb | detectLesion(row)
		else:
			rlt_knowledge['code'] = rlt_knowledge['code'] | detectCTcode(row)
			rlt_knowledge['date'] = rlt_knowledge['date'] | detectDate(row)
			rlt_knowledge['lesion_highriskplq_flag'] = analyze_conclusion(row)
			finding_kb = finding_kb | detectLesion(row)

	for k, v in rlt_knowledge.items():
		if type(v) == set:
			for v_ in v:
				return_txt = return_txt + '\n' + 'CT_' + k + ': ' + v_
				# tmp_txt = 'CT_' + k + ': ' + v_
				return_list_info.append((k, v_))
		# print ('CT', k, v_)
		else:
			# print ('CT', k, v)
			return_txt = return_txt + '\n' + 'CT_' + k + ': ' + str(v)
			tmp_txt = 'CT_' + k + ': ' + str(v)
			return_list_info.append((k, str(v)))

	return_txt = return_txt + '\n\n'
	for (a, b, c) in sorted(finding_kb):
		return_txt = return_txt + '\n' + '< ' + a + ',  ' + b + ',  ' + c + '>'
		# tmp_txt = '('+a + ', '+ b + ', '+ c +')'
		return_list_triple.append((a, b, c))
	# print (a,b,c)

	return return_list_info, return_list_triple


def detectDate(sen):
	import re

	re1 = '.*?'  # Non-greedy match on filler
	re2 = '((?:(?:[1]{1}\\d{1}\\d{1}\\d{1})|(?:[2]{1}\\d{3}))(?:[0]?[1-9]|[1][012])(?:(?:[0-2]?\\d{1})|(?:[3][01]{1})))(?![\\d])'  # YYYYMMDD 1

	rg = re.compile(re1 + re2, re.IGNORECASE | re.DOTALL)

	m = rg.search(sen)
	if m:
		yyyymmdd = m.group(1)
		return set([yyyymmdd])
	else:
		return set([])


def detectCTcode(sen):
	code_set = set([])
	ct_code_dict = {
		'CT, calcium scoring': 'CAC',
		'CT, Coronary Artery (Post OP)': 'post-CABG',
		'LIMA to LAD': 'post-CABG',
		's/p CABG': 'post-CABG',
		's/p PCI': 'post-PCI',
		's/p coronary stent implantation': 'post-PCI',
		'stent': 'post-PCI',
		'in-stent restenosis': 'post-PCI',
		'CT, Coronary Artery': 'native-CA',
		'CT, Coronary Artery (GHE)': 'native-CA',
		'CT, Coronary Artery (Lung)': 'native-CA',
		'CT, Coronary Artery + Aortic Dissection': 'native-CA',
		'CT, Coronary Artery (Valve)': 'native-CA',
		'CT, Coronary Artery (Post OP Valve)': 'native-CA',
		'CT,Heart (Adult)': 'native-CA',
		'MR,': 'CMR'
	}

	for k, v in ct_code_dict.items():
		if k.lower() in sen.lower():
			code_set.add(v)

	return code_set


def analyze_conclusion(sen):
	# hight risk plaque
	rules_hight_risk_plaque = [
		'high risk plaque morphology',
		'high-risk plaque morphology',
		'low attenuation plaque',
		'positive remodel',
		'spotty calcium',
		'napkin-ring sign'
	]

	for rule in rules_hight_risk_plaque:
		if rule in sen:
			return True
		else:
			return False



abb_info = {}
with open('./extract/abbdata_v2.tsv', 'r', encoding='utf-8') as f:
	lines = f.readlines()
	for line in lines:
		token = line.strip().split('\t')
		abb_info[token[1].lower()] = list(map(lambda x: x.lower(), token[2:]))

meta_info = {}
with open('./extract/metadata_v2.tsv', 'r', encoding='utf-8') as f:
	lines = f.readlines()
	for line in lines:
		token = line.strip().split('\t')
		meta_info[token[1].lower()] = token[0].lower()

def detectLesion(sen):
	sen = preprocess(sen)
	sen_ = sen.split()

	extracted_entity = []
	entities = []
	for token in sen_:
		t = token.strip().lower()
		entities = []
		for mention in abb_info.keys():
			if mention in t:
				entities += abb_info[mention]
		for s in ['rca', 'lad', 'lcx']:
			Flag = True
			for entity in entities:
				if s in entity:
					Flag = False
			if Flag and s in t:
				entities += ['p' + s, 'm' + s, 'd' + s]
		for s in ['om']:
			Flag = True
			for entity in entities:
				if s in entity:
					Flag = False
			if Flag and s in t:
				entities += ['om1', 'om2']
		# print(t, entities)
		for e in entities:
			if e not in extracted_entity:
				extracted_entity.append(e)

	segment_list = []
	knowledges = []
	segment_reset = False
	for e in extracted_entity:
		t = meta_info[e]

		if t == 'segment':
			if segment_reset:
				segment_list = []
				segment_reset = False
			else:
				segment_list.append(e)
		elif t == 'stenosis_degree':
			for segment in segment_list:
				knowledges.append((segment, t, e))
			segment_reset = True
		elif t == 'plaque_type':
			for segment in segment_list:
				knowledges.append((segment, t, e))
			segment_reset = True

	return set(knowledges)


def preprocess(sen):
	import re
	rule_dict = {
		'< 10 mm': 'discrete',
		'< 10mm': 'discrete',
		'10 mm': 'discrete',
		'10': 'tubular',
		'10-20 mm': 'tubular',
		'10-20mm': 'tubular',
		'11 mm': 'tubular',
		'12 mm': 'tubular',
		'13 mm': 'tubular',
		'14 mm': 'tubular',
		'15 mm': 'tubular',
		'16 mm': 'tubular',
		'17 mm': 'tubular',
		'18 mm': 'tubular',
		'19 mm': 'tubular',
		'>20 mm': 'diffuse',
		'> 20 mm': 'diffuse',
		' 30': 'diffuse'
	}

	for r in rule_dict.keys():
		if r in sen:
			sen = sen.replace(r, rule_dict[r])

	# 예약어 제거
	sen = sen.replace('[Finding]: ', '')
	sen = sen.replace('[Conclusion]: ', '')

	# 특수문자 제거
	sen = sen.replace('/', ' ')
	sen = re.sub('[-=.#?:$}]', '', sen)

	# multiple string 제거
	sen = ' '.join(sen.split())

	return sen

def format_unity(triples):
	vessels = ['PRCA', 'MRCA', 'DRCA', 'PLAD', 'MLAD', 'DLAD', 'PLCX', 'DLCX', 'RPDA', 'LPDA', 'RPLB', 'LPLB', 'LM', 'D1', 'D2', 'OM1', 'OM2', 'RI']
	stenosis_mapping = {"normal": 0, "minimal": 1, "mild": 2, "moderate": 3, "severe": 4, "occlusion": 5, "uninterpretable": 6}
	plaque_mapping = {"no_plaque": 0, "calcified": 1, "mixed": 2, "noncalcified": 3}
	output_dict = collections.defaultdict(int)

	for triple in triples:
		try:
			s = triple[0]
			p = triple[1]
			o = triple[2]
			if p == 'stenosis_degree':
				output_dict['s_' + s.upper()] = stenosis_mapping[o]
			elif p == 'plaque_type':
				output_dict['p_' + s.upper()] = plaque_mapping[o]
			else:
				continue
		except Exception as e:
			print(e)
			print(triple)

	return output_dict


def measure(input_dir, output_path):
	filenames = os.listdir(input_dir)
	output = list()
	for filename in filenames:
		with open(os.path.join(input_dir, filename), 'r', encoding='utf-8') as f:
			content = f.read()
			predict_triple = format_unity(process(content)[1])
			output.append({
				"filename": filename,
				"triples": predict_triple
			})
			print(filename, predict_triple)

	with open(output_path, 'w', encoding='utf-8') as f:
		json.dump(output, f, ensure_ascii=False, indent='\t')
	return


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("-input_dir", default="./input")
	parser.add_argument("-output_path", default="./output/sample_result.json")

	args = parser.parse_args()

	measure(args.input_dir, args.output_path)
