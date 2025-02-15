test: tests
tests:
	python -m coverage run -am mouse._mouse_tests
	python -m coverage report && coverage3 html

build: tests mouse setup.py README.md CHANGES.md MANIFEST.in
	python ../docstring2markdown/docstring2markdown.py mouse "https://github.com/boppreh/mouse/blob/master" > README.md
	find . \( -name "*.py" -o -name "*.sh" -o -name "* .md" \) -exec dos2unix {} \;
	python setup.py sdist --format=zip bdist_wheel && twine check dist/*

release:
	python make_release.py

clean:
	rm -rfv dist build coverage_html_report mouse.egg-info
