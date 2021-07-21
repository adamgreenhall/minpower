build:
	# ref: https://packaging.python.org/tutorials/packaging-projects/
	pip install --upgrade build twine
	python3 -m build
	twine upload dist/*
