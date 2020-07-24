import json

data = []
with open('/home/gocks456/pybossa/project_order/Emotion_test1/sentence_task2_temp.json', encoding='utf-8') as f, \
		open('/home/gocks456/pybossa/project_order/Emotion_test1/sentence_task2.json', "w", encoding='utf-8') as ff:
	for line in f:
		data.append(json.loads(line))

	ff.write(json.dumps(data, ensure_ascii=False))
