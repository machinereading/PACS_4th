from error_detection_v1 import detect_error
import argparse

def evalute(pred_path, gold_path, error_type):
	pred_datas = open(pred_path, 'r', encoding='utf-8').readlines()
	gold_datas = open(gold_path, 'r', encoding='utf-8').readlines()

	tp = 0
	fp = 0
	fn = 0
	for pred_data, gold_data in zip(pred_datas, gold_datas):
		splited_pred = pred_data.strip().split('\t')
		ID = splited_pred[0]
		if len(splited_pred) == 2:
			pred = splited_pred[1]
		pred_errors = set(pred.strip().split())

		ID, gold = gold_data.strip().split('\t')
		gold_errors = set(gold.strip().split())

		tp += len(pred_errors & gold_errors)
		fp += len(pred_errors - gold_errors)
		fn += len(gold_errors - pred_errors)

	# print(tp, fp, fn)
	precision = tp / (tp + fp)
	recall = tp / (tp + fn)
	f1 = (2 * precision * recall) / (precision + recall)

	return precision, recall, f1, tp, fp, fn


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Evaluate performance of error detection.')
	parser.add_argument('--pred_dir', type=str, default='./output/')
	parser.add_argument('--gold_dir', type=str, default='./gold/')
	parser.add_argument('--error_type', type=str, help='error type of radiology findings')

	print("Start Evaluating Performance\n")
	args = parser.parse_args()
	print("pred_dir : %s" % args.pred_dir)
	print("gold_dir : %s" % args.gold_dir)
	print("error_type : %s\n" % args.error_type)
	if args.error_type == 'all':
		pred_path = args.pred_dir + 'typing_output.tsv'
		gold_path = args.gold_dir + 'typing_gold.tsv'
		_, rec1, _, tp_1, fp_1, fn_1 = evalute(pred_path, gold_path, 'typing')
		# print("typing", ':', rec1)
		pred_path = args.pred_dir + 'date_output.tsv'
		gold_path = args.gold_dir + 'date_gold.tsv'
		_, rec2, _, tp_2, fp_2, fn_2 = evalute(pred_path, gold_path, 'date')
		# print("date", ':', rec2)
		rec = (tp_1 + tp_2) / (tp_1 + fn_1 + tp_2 + fn_2)

	else :
		pred_path = args.data_dir + args.error_type + '_output.tsv'
		gold_path = args.data_dir + args.error_type + '_gold.tsv'
		pre, rec, f1, _, _, _ = evalute(pred_path, gold_path, args.error_type)
	print('자연어처리 기반 판독문 오류 감지율 :', round(rec*100, 2))
	print()
	print("Finish Evaluating Performance")

	# print(check_error('../validated_json/date_discrepancy_error.json', 'date'))