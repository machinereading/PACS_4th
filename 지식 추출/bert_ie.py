import numpy as np
import json
import torch
from torch.utils.data import Dataset, DataLoader
from pytorch_transformers import BertTokenizer, BertForSequenceClassification, BertConfig

import torch.nn as nn
from torch.optim import Adam
import torch.nn.functional as F

tokenizer = BertTokenizer.from_pretrained("bert-base-multilingual-cased", do_lower_case=True)
device = torch.device("cpu")

def text_processing(lines, Max_len):
	input_ids = []
	mask_ids = []
	token_type_ids = []
	for line in lines:
		# [cls], [sep] 추가 Max_len 길이 맞추기
		encoded_line = tokenizer.encode(line, add_special_tokens=True)
		input = encoded_line + [0] * (Max_len - len(encoded_line))
		token_type = [0] * len(input)
		mask = [1] * len(encoded_line) + [0] * (Max_len - len(encoded_line))
		input_ids.append(torch.tensor(input).to(device))
		token_type_ids.append(torch.tensor(token_type).to(device))
		mask_ids.append(torch.tensor(mask).to(device))

	return input_ids, token_type_ids, mask_ids


class BertCls_dataset(Dataset):
	def __init__(self, input_ids, token_type_ids, mask_ids, label):
		self.input = input_ids
		self.token_type = token_type_ids
		self.attn_mask = mask_ids
		self.label = label

	def __len__(self):
		return len(self.input)

	def __getitem__(self, idx):
		x = self.input[idx]
		y = self.token_type[idx]
		z = self.attn_mask[idx]
		label = self.label[idx]
		label = [label]

		return x, y, z, torch.tensor(label).long().to(device)


# label 숫자로 바꾸기
def label_convert(label):
	for i in range(len(label)):
		if label[i]:
			label[i] = 0
		else:
			label[i] = 1
	return label


def train(Batch_size, Max_len, epochs):
	with open('../validated_json/train.IE.json', 'r', encoding='utf-8') as f:
		train_data = json.load(f)
	with open('../validated_json/valid.IE.json', 'r', encoding='utf-8') as f:
		valid_data = json.load(f)

	train_text = list(map(lambda x: x['text'], train_data))
	valid_text = list(map(lambda x: x['text'], valid_data))

	train_label = label_convert([x['relation'] for x in train_data])
	valid_label = label_convert([x['relation'] for x in valid_data])

	train_input_ids, train_token_type_ids, train_mask_ids = text_processing(train_text, Max_len)
	valid_input_ids, valid_token_type_ids, valid_mask_ids = text_processing(valid_text, Max_len)

	train_dataset = BertCls_dataset(train_input_ids, train_token_type_ids, train_mask_ids, train_label)
	valid_dataset = BertCls_dataset(valid_input_ids, valid_token_type_ids, valid_mask_ids, valid_label)

	train_dataloader = DataLoader(train_dataset, batch_size=Batch_size, shuffle=True)
	valid_dataloader = DataLoader(valid_dataset, batch_size=Batch_size, shuffle=True)

	model = BertForSequenceClassification.from_pretrained(
		"bert-base-multilingual-cased",  # Use the 12-layer BERT model, with an uncased vocab.
		num_labels=2,  # The number of output labels--2 for binary classification.
		# You can increase this for multi-class tasks.
		output_attentions=False,  # Whether the model returns attentions weights.
		output_hidden_states=False,  # Whether the model returns all hidden-states.
	)
	model.to(device)
	model.train()

	optimizer = Adam(model.parameters(), lr=1e-6)

	itr = 1
	p_itr = 100
	total_loss = 0
	total_len = 0
	total_correct = 0

	for epoch in range(epochs):
		for inputs, _, _, labels in train_dataloader:
			outputs = model(inputs, labels=labels)
			loss, logits = outputs
			pred = torch.argmax(F.softmax(logits), dim=1)
			correct = pred.eq(labels.squeeze())
			total_correct += correct.sum().item()
			total_len += len(labels)
			total_loss += loss.item()
			loss.backward()
			optimizer.step()

			if itr % p_itr == 0:
				print(
					'[Epoch {}/{}] Iteration {} -> Train Loss: {:.4f}, Accuracy: {:.3f}'.format(epoch + 1, epochs, itr,
					                                                                            total_loss / p_itr,
					                                                                            total_correct / total_len))
				total_loss = 0
				total_len = 0
				total_correct = 0

			itr += 1
		torch.save(model.state_dict(), '../ie_models/ie.epoch{:d}'.format(epoch))


def test(testset, Batch_size, Max_len, epoch):
	with open(testset, 'r', encoding='utf-8') as f:
		test_data = json.load(f)
	test_text = list(map(lambda x: x['text'], test_data))

	test_label = label_convert([x['relation'] for x in test_data])

	test_input_ids, train_token_type_ids, train_mask_ids = text_processing(test_text, Max_len)

	test_dataset = BertCls_dataset(test_input_ids, train_token_type_ids, train_mask_ids, test_label)

	test_dataloader = DataLoader(test_dataset, batch_size=Batch_size, shuffle=True)

	model = BertForSequenceClassification.from_pretrained(
		"bert-base-multilingual-cased",  # Use the 12-layer BERT model, with an uncased vocab.
		num_labels=2,  # The number of output labels--2 for binary classification.
		# You can increase this for multi-class tasks.
		output_attentions=False,  # Whether the model returns attentions weights.
		output_hidden_states=False,  # Whether the model returns all hidden-states.
	)
	model.load_state_dict(torch.load('../ie_models/ie.epoch{:d}'.format(3)))
	model.to(device)
	model.eval()

	total_len = 0
	total_correct = 0
	preds = []
	for inputs, _, _, labels in test_dataloader:
		outputs = model(inputs, labels=labels)
		loss, logits = outputs
		pred = torch.argmax(F.softmax(logits), dim=1)
		preds += list(pred)
		correct = pred.eq(labels.squeeze())
		total_correct += correct.sum().item()
		total_len += len(labels)
	print(
		'[Epoch {}] -> valid, Accuracy: {:.3f}'.format(epoch + 1, total_correct / total_len))
	return pred


def predict(model, test_data, Batch_size, Max_len):
	test_text = list(map(lambda x: x['text'], test_data))

	test_label = label_convert([x['relation'] for x in test_data])

	test_input_ids, train_token_type_ids, train_mask_ids = text_processing(test_text, Max_len)

	test_dataset = BertCls_dataset(test_input_ids, train_token_type_ids, train_mask_ids, test_label)

	test_dataloader = DataLoader(test_dataset, batch_size=Batch_size, shuffle=False)

	preds = []
	for inputs, _, _, labels in test_dataloader:
		outputs = model(inputs, labels=labels)
		loss, logits = outputs
		pred = torch.argmax(F.softmax(logits), dim=1)
		preds += list(pred)

	return pred


def load_model(model_path):
	model = BertForSequenceClassification.from_pretrained(
		"bert-base-multilingual-cased",  # Use the 12-layer BERT model, with an uncased vocab.
		num_labels=2,  # The number of output labels--2 for binary classification.
		# You can increase this for multi-class tasks.
		output_attentions=False,  # Whether the model returns attentions weights.
		output_hidden_states=False,  # Whether the model returns all hidden-states.
	)
	model.load_state_dict(torch.load(model_path, map_location=device))
	model.to(device)
	return model

if __name__ == '__main__':
	train(Batch_size=16, Max_len=120, epochs=4)
	# predict(testset="../validated_json/train.IE.json", Batch_size=16, Max_len=120)
	# predict(test_data="../validated_json/train.IE.json", Batch_size=16, Max_len=120)
	pass