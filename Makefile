CONFIG ?= config.yaml

.PHONY: dev test screenshot deploy

dev:
	python -m src.main --config $(CONFIG) --once

test:
	python -m src.main --config $(CONFIG) --test

screenshot:
	python -m src.main --config config.example.yaml --test

deploy:
	rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
		. pi@raspberrypi.local:/home/pi/sfmta-arrivals/
	ssh pi@raspberrypi.local 'cd /home/pi/sfmta-arrivals && sudo systemctl restart sfmta-arrivals'
