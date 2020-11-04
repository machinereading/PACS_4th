import json
import re
import nltk
from nltk.util import ngrams
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
from tqdm import tqdm
import argparse



tri_frequency = json.load(open('./typing_info/tri_frequency.json', 'r', encoding='utf-8'))
tri_vocab = json.load(open('./typing_info/tri_vocab.json', 'r', encoding='utf-8'))

class Error():
	def __init__(self, sentence):
		# preparation for spell_check
		self.laterality_word_set = {'LEFT', 'Left', 'left', 'Lt', 'RIGHT', 'Right', 'right', 'Rt', 'both', 'bilateral'}
		self.left_words = ['LEFT', 'Left', 'left', 'Lt']
		self.right_words = ['RIGHT', 'Right', 'right', 'Rt']
		self.both_words = ['both', 'bilateral']

		self.stopWords = set(stopwords.words('english'))
		self.ps = PorterStemmer()

		self.sentence = sentence
		self.tokens = nltk.word_tokenize(self.sentence)
		self.date_reg_exp = re.compile('(\d{4})[/,-]*(\d{1,2})[/,-]*(\d{1,2})')

	def typing_error(self, theta1, theta2):
		'''
		typing error 체크.
		:param sentences: (list): list of strings
		:param theta: (float): 오류 판정 threshold
		:return return_pairs: (list): ori 문장-수정된 문장 페어 리스트
		'''
		error_token = set()
		sep = ':-:'
		min_edit = 4

		tokens = nltk.word_tokenize(self.sentence)
		refined_tokens = []
		for token in tokens:
			if any(char.isdigit() for char in token):
				continue
			else:
				refined_tokens.append(token)
		for trigram in ngrams(refined_tokens, 3):
			given_phrase = sep.join(trigram)
			pre_tok, target_tok, next_tok = trigram[0], trigram[1], trigram[2]
			total_freq = 0
			try:
				for predict_tok in tri_vocab[pre_tok + sep + next_tok]:
					predict_phrase = pre_tok + sep + predict_tok + sep + next_tok
					total_freq = total_freq + tri_frequency[predict_phrase]
				# if target_tok == 'Maderote':
				# 	print(pre_tok, next_tok)

				ambiguity = len(tri_vocab[pre_tok + sep + next_tok])
				theta = theta1
				for predict_tok in tri_vocab[pre_tok + sep + next_tok]:
					predict_phrase = pre_tok + sep + predict_tok + sep + next_tok
					if predict_phrase != given_phrase:
						prob = round(tri_frequency[predict_phrase] / float(total_freq), 5)
						if nltk.edit_distance(target_tok, predict_tok) < len(target_tok):
							if nltk.edit_distance(target_tok, predict_tok) < min_edit:
								if total_freq < 5:
									error_token.add(target_tok)
								else:
									if ambiguity >= 5:
										theta = theta2
									# elif ambiguity >= 3:
									# 	theta = 0.5
									if prob >= theta:
										error_token.add(target_tok)

			except KeyError as k:
				# print(k)
				# print(pre_tok + sep + next_tok)
				pass

		return error_token

	def date_error(self):
		"""
		날짜 선후관계 파악.
		"""

		def chk_date(date1, date2):
			try:
				if int(date1[0]) > int(date2[0]):
					return True
				elif int(date1[0]) == int(date2[0]):
					if int(date1[1]) > int(date2[1]):
						return True
					elif int(date1[1]) == int(date2[1]):
						if int(date1[2]) > int(date2[2]):
							return True
						else:
							return False
					else:
						return False
				else:
					return False
			except IndexError:
				return True

		order_vocab = ['previous', 'since', 'compare', 'compared', 'Compare', 'Compared', 'comparison', 'refer', 'CT', 'state']
		# order_vocab = ['previous', 'since', 'compare', 'compared', 'Compare', 'Compared', 'comparison', 'refer']
		reading_date = ()
		previous_date = []
		Flag = True
		Start_findings = True
		for i, token in enumerate(self.tokens):
			if token == 'Findings':
				Start_findings = False
			if Flag:
				if token == '*':
					Flag = False
					continue
				else :
					date = self.date_reg_exp.findall(token)
					if date != []:
						reading_date = date[0]
						# print("reading_date" ,reading_date)
			else:
				st = i-4 if i - 4 >= 0 else 0
				date = self.date_reg_exp.findall(token)
				# print("previous_date", date)
				for SPE in order_vocab:
					if date != []:
						if SPE in self.tokens[st:i] or Start_findings:
						# if SPE in self.tokens[st:i]:
							previous_date += date

		result = set()
		for date in previous_date:
			if not chk_date(reading_date, date):
				result.add('-'.join(date))

		return result


def detect_error(text, error_type):
	e = Error(text)
	if error_type == 'typing':
		detected_errors = e.typing_error(0.7, 0.3)
	elif error_type == 'date':
		detected_errors = e.date_error()

	return detected_errors


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Detect natural language errors.')
	parser.add_argument('-input_dir', type=str, default='./input/')
	parser.add_argument('-output_dir', type=str, default='./output/')
	parser.add_argument('-error_type', type=str, default='all', help='error type of radiology findings')

	args = parser.parse_args()
	print("Start error_detection_v1")
	print("input_dir : %s" % args.input_dir)
	print("output_dir : %s" % args.output_dir)
	print("error_type : %s\n" % args.error_type)
	if args.error_type == 'all':
		# print("Detecting typing error")
		input_path = args.input_dir + 'typing_input.tsv'
		input_datas = open(input_path, 'r', encoding='utf-8').readlines()
		del input_datas[0]
		output_f = open(args.output_dir + "typing_output.tsv", 'w', encoding='utf-8')
		output_f.write('ID\tOUTPUT\n')
		for input_data in tqdm(input_datas, desc="typing"):
			ID, text = input_data.strip().split('\t')
			detected_errors = detect_error(text, "typing")
			output_text = str(ID) + '\t' + ' '.join(detected_errors) + '\n'
			output_f.write(output_text)

		# print("Detecting date error")
		input_path = args.input_dir + 'date_input.tsv'
		input_datas = open(input_path, 'r', encoding='utf-8').readlines()
		del input_datas[0]
		output_f = open(args.output_dir + "date_output.tsv", 'w', encoding='utf-8')
		output_f.write('ID\tOUTPUT\n')
		for input_data in tqdm(input_datas, desc="date"):
			ID, text = input_data.strip().split('\t')
			detected_errors = detect_error(text, "date")
			output_text = str(ID) + '\t' + ' '.join(detected_errors) + '\n'
			output_f.write(output_text)
	else :
		# print("Detecting %s error" % args.error_type)
		input_path = args.data_dir + args.error_type + '_input_tsv'
		input_datas = open(input_path, 'r', encoding='utf-8').readlines()
		del input_datas[0]
		output_f = open(args.output_dir + args.error_type + "_output.tsv", 'w', encoding='utf-8')
		output_f.write('ID\tOUTPUT\n')
		for input_data in tqdm(input_datas, desc=args.error_type):
			ID, text = input_data.strip().split('\t')
			detected_errors = detect_error(text, args.error_type)
			output_text = str(ID) + ' ' + ' '.join(detected_errors) + '\n'
			output_f.write(output_text)
	print("Finish error_detection_v1")