import collections
import json
from bert_ie import predict, load_model
from tqdm import tqdm
import argparse, os

def process(string, model):
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

			finding_kb = finding_kb | detectLesion(row, model)
		else:
			rlt_knowledge['code'] = rlt_knowledge['code'] | detectCTcode(row)
			rlt_knowledge['date'] = rlt_knowledge['date'] | detectDate(row)
			rlt_knowledge['lesion_highriskplq_flag'] = analyze_conclusion(row)
			finding_kb = finding_kb | detectLesion(row, model)

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

def detectLesion(sen, model):
	sen = preprocess(sen)
	total_mentions = detectEntity(sen)

	knowledges = []
	if total_mentions == []:
		return set()
	# print(total_mentions)
	target_mentions = list(
		filter(lambda x: x['type'] in ['segment', 'plaque_type', 'stenosis_degree'], total_mentions))
	types = set(list(map(lambda x: x['type'], target_mentions)))
	if len(set(types)) < 2 or 'segment' not in types:
		return set()
	new_sentence = ' '.join(sen.split()).lower()
	segments = list(filter(lambda x: x['type'] == 'segment', target_mentions))
	plaque_types = list(filter(lambda x: x['type'] == 'plaque_type', target_mentions))
	stenosis_degrees = list(filter(lambda x: x['type'] == 'stenosis_degree', target_mentions))
	lesion_lengths = list(filter(lambda x: x['type'] == 'lesion_length', total_mentions))
	e1s = '[unused1]'
	e1e = '[unused2]'
	e2s = '[unused3]'
	e2e = '[unused4]'
	format_data = []
	for segment in segments:
		for plaque_type in plaque_types:
			format_data.append({
				"segment": segment['surface'],
				"plaque_type": plaque_type['surface'],
				"text": new_sentence.replace(segment['surface'].lower(),
				                             e1s + segment['surface'].lower() + e1e).replace(
					plaque_type['surface'].lower(), e2s + plaque_type['surface'].lower() + e2e),
				"relation": True
			})
		for stenosis_degree in stenosis_degrees:
			format_data.append({
				"segment": segment['surface'],
				"stenosis_degree": stenosis_degree['surface'],
				"text": new_sentence.replace(segment['surface'].lower(),
				                             e1s + segment['surface'].lower() + e1e).replace(
					stenosis_degree['surface'].lower(), e2s + stenosis_degree['surface'].lower() + e2e),
				"relation": True
			})
	if len(format_data) > 0:
		preds = predict(model, format_data, Batch_size=16, Max_len=120)
		for data, pred in zip(format_data, preds):
			if pred == 0:
				entities = list(filter(lambda x: x['surface'] == data['segment'], segments))[0]['entities']
				if 'plaque_type' in data.keys():
					for entity in entities:
						knowledges.append((entity, 'plaque_type', data['plaque_type']))
				elif 'stenosis_degree' in data.keys():
					for entity in entities:
						knowledges.append((entity, 'stenosis_degree', data['stenosis_degree']))
	for segment in segments:
		entities = segment['entities']
		for lesion_length in lesion_lengths:
			for entity in entities:
				knowledges.append((entity, 'lesion_length', lesion_length['entities'][0]))
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
			pass
			# print(e)
			# print(triple)
			# print(Exception)

	return output_dict


def measure(input_dir, output_path, model_path):
	print("model loading")
	model = load_model(model_path)
	model.eval()
	filenames = os.listdir(input_dir)
	output = list()
	for filename in tqdm(filenames):
		with open(os.path.join(input_dir, filename), 'r', encoding='utf-8') as f:
			content = f.read()
			info_list, triple_list = process(content, model)
			# print(info_list)
			date = ""
			code = ""
			lesion_highriskplq_flag = False
			for e in info_list:
				if "date" == e[0]:
					date = e[1]
				elif "code" == e[0]:
					code = e[1]
				elif "lesion_highriskplq_flag" == e[0]:
					lesion_highriskplq_flag = e[1]

			# print(triple_list)
			predict_triple = format_unity(triple_list)
			output.append({
				"filename": filename,
				"date": date,
				"code": code,
				"lesion_highriskplq_flag": lesion_highriskplq_flag,
				"lesions": predict_triple
			})
			# print(filename, predict_triple)

	with open(output_path, 'w', encoding='utf-8') as f:
		json.dump(output, f, ensure_ascii=False, indent='\t')
	return

def prepare():
	dataset = json.load(open('../validated_json/IE_data.json', 'r', encoding='utf-8'))
	stenosis_mapping = {"normal": 0, "minimal": 1, "mild": 2, "moderate": 3, "severe": 4, "occlusion": 5,
	                    "uninterpretable": 6}
	plaque_mapping = {"no_plaque": 0, "calcified": 1, "mixed": 2, "noncalcified": 3}
	format_data = []
	e1s = '[unused1]'
	e1e = '[unused2]'
	e2s = '[unused3]'
	e2e = '[unused4]'
	for instance in dataset:
		content = instance['content']
		triples = instance['triples']

		# print(content)
		for sen in content.split('\n'):
			mentions = detectEntity(sen)

			if mentions == []:
				continue
			# else:
			# 	print(mentions)

			target_mentions = list(filter(lambda x: x['type'] in ['segment', 'plaque_type', 'stenosis_degree'], mentions))
			types = set(list(map(lambda x: x['type'], target_mentions)))
			if len(set(types)) >= 2 and 'segment' in types:
				new_sentence = ' '.join(sen.split()).lower()
				segments = list(filter(lambda x: x['type'] == 'segment', target_mentions))
				plaque_types = list(filter(lambda x: x['type'] == 'plaque_type', target_mentions))
				stenosis_degrees = list(filter(lambda x: x['type'] == 'stenosis_degree', target_mentions))
				for segment in segments:
					if 'p_' + segment['entities'][0].upper() not in triples.keys() or 's_' + segment['entities'][0].upper() not in triples.keys():
						continue
					for plaque_type in plaque_types:
						if triples['p_' + segment['entities'][0].upper()] == plaque_mapping[plaque_type['entities'][0]]:
							format_data.append({
								"text": new_sentence.replace(segment['surface'].lower(), e1s + segment['surface'].lower() + e1e).replace(plaque_type['surface'].lower(), e2s + plaque_type['surface'].lower() + e2e),
								"relation": True
							})
						else:
							format_data.append({
								"text": new_sentence.replace(segment['surface'].lower(),
								                             e1s + segment['surface'].lower() + e1e).replace(
									plaque_type['surface'].lower(), e2s + plaque_type['surface'].lower() + e2e),
								"relation": False
							})
					for stenosis_degree in stenosis_degrees:
						if triples['s_' + segment['entities'][0].upper()] == stenosis_mapping[stenosis_degree['entities'][0]]:
							format_data.append({
								"text": new_sentence.replace(segment['surface'].lower(), e1s + segment['surface'].lower() + e1e).replace(stenosis_degree['surface'].lower(), e2s + stenosis_degree['surface'].lower() + e2e),
								"relation": True
							})
						else:
							format_data.append({
								"text": new_sentence.replace(segment['surface'].lower(),
								                             e1s + segment['surface'].lower() + e1e).replace(
									stenosis_degree['surface'].lower(), e2s + stenosis_degree['surface'].lower() + e2e),
								"relation": False
							})

	with open('../validated_json/IE.json', 'w', encoding='utf-8') as f:
		json.dump(format_data, f, ensure_ascii=False, indent='\t')
	with open('../validated_json/train.IE.json', 'w', encoding='utf-8') as f:
		json.dump(format_data[:int(len(format_data)*0.8)], f, ensure_ascii=False, indent='\t')
	with open('../validated_json/valid.IE.json', 'w', encoding='utf-8') as f:
		json.dump(format_data[int(len(format_data)*0.8):int(len(format_data)*0.9)], f, ensure_ascii=False, indent='\t')
	with open('../validated_json/test.IE.json', 'w', encoding='utf-8') as f:
		json.dump(format_data[int(len(format_data)*0.9):], f, ensure_ascii=False, indent='\t')


def detectMention(sen):
	sen = preprocess(sen)
	sen_ = sen.split()

	mentions = set()
	for token in sen_:
		t = token.strip().lower()
		is_abb = False
		for abb_mention in abb_info.keys():
			if abb_mention in t:
				mentions.add(t)
				is_abb = True
				break
		if not is_abb:
			Flag = True
			for high_mention in ['rca', 'lad', 'lcx', 'om']:
				for mention in list(mentions):
					if high_mention in mention:
						Flag = False
				if Flag and high_mention in t:
					mentions.add(t)
					break

	return list(mentions)


def detectEntity(sen):
	sen = preprocess(sen)
	sen_ = sen.split()

	mentions = list()
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
		if entities != []:
			mentions.append({
				"surface": token,
				"entities": entities
			})

	for mention in mentions:
		mention['type'] = meta_info[mention['entities'][0]]

	return list(mentions)


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("-input_dir", default="./input")
	parser.add_argument("-output_path", default="./output/sample_result.json")
	parser.add_argument("-model_path", default="./models/ie.epoch3")

	args = parser.parse_args()
	measure(args.input_dir, args.output_path, args.model_path)