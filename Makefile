.PHONY: setup ingest run eval test clean

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

ingest:
	python run_ingest.py

run:
	python app.py

eval:
	python eval/run_eval.py

test:
	pytest -q

clean:
	rm -rf data/chroma __pycache__ .pytest_cache
