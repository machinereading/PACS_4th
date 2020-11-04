import json


def make_IO():
	error_json = json.load(open('./data/date_error.json', 'r', encoding='utf-8'))

	input_text = 'ID\tINPUT_TEXT\n'
	output_text = 'ID\tOUTPUT\n'

	for i, unit in enumerate(error_json):
		input_text += str(i) + '\t' + unit['negative_sentence'] + '\n'
		output_text += str(i) + '\t' + ' '.join(unit['negative_target']) + '\n'

	with open('./data/date_input.tsv', 'w', encoding='utf-8') as f:
		f.write(input_text)
	with open('./data/date_output.tsv', 'w', encoding='utf-8') as f:
		f.write(output_text)


if __name__ == '__main__':
	make_IO()