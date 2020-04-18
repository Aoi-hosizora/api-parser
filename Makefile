install:
	python3 setup.py bdist_egg
	easy_install .\dist\apiparser-1.0.0-py3.6.egg

uninstall:
	easy_install -m apiparser==1.0.0

.PHONY install uninstall
