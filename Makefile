release:
	# ref: https://packaging.python.org/tutorials/packaging-projects/
	pip install --upgrade build twine
	rm -r dist/
	python3 -m build
	twine upload dist/*
