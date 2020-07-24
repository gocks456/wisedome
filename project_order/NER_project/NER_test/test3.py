import json

data = []
with open('/home/gocks456/project_order/NER_test/practice.json', encoding='utf-8') as f, \
		open('/home/gocks456/project_order/NER_test/1_pratice.json', "w", encoding='utf-8') as ff:
	for line in f:
		data.append(json.loads(line))

	ff.write(json.dumps(data, ensure_ascii=False))
