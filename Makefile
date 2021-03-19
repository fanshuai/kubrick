pip_install:
	pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ --default-timeout=100
	pip install --upgrade -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --default-timeout=100
local_config:
	pwd
dev_migrate:
	python manage.py makemigrations
	python manage.py migrate --settings=kubrick.settings
	python manage.py migrate --settings=kubrick.djadmin.settings
	python manage.py clearsessions
dev_start:
	python manage.py runserver 0.0.0.0:5566
dev_init:
	mkdir -p /data/logs/kubrick
	pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ --default-timeout=100
	pip install --upgrade -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --default-timeout=100
	python manage.py collectstatic --noinput --settings=kubrick.djadmin.settings
	python manage.py silk_clear_request_log --settings=kubrick.djadmin.settings
	python manage.py migrate --settings=kubrick.djadmin.settings
	python manage.py clearcache --alias=default,session
	python manage.py clearsessions
	echo "" >> frontend/public/assets/.gitkeep

sit_migrate:
	RUN_ENV="sit" python manage.py migrate --settings=kubrick.settings
	RUN_ENV="sit" python manage.py migrate --settings=kubrick.djadmin.settings

prod_install:
	RUN_ENV="prod" python manage.py migrate --settings=kubrick.settings
	RUN_ENV="prod" python manage.py migrate --settings=kubrick.djadmin.settings
	RUN_ENV="prod" python manage.py collectstatic --noinput --settings=kubrick.djadmin.settings
	RUN_ENV="prod" python manage.py clearcache --alias=default,session
	RUN_ENV="prod" python manage.py clearsessions

assemble:
	mkdir -p /data/logs/kubrick
	pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ --default-timeout=100
	pip install --upgrade -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --default-timeout=100
	RUN_ENV="prod" python manage.py migrate --settings=kubrick.djadmin.settings
	RUN_ENV="prod" python manage.py clearcache --alias=default,session
	RUN_ENV="prod" python manage.py clearsessions
install:
	RUN_ENV="prod" python manage.py clearcache --alias=session
	RUN_ENV="prod" python manage.py collectstatic --noinput --settings=kubrick.djadmin.settings
	cp ./config/conf/nginx/conf.d/kubrick-prod.conf /opt/nginx/conf/vhosts/
start_djadmin:
	RUN_ENV="prod" python manage.py runserver 0.0.0.0:5577 --settings=kubrick.djadmin.settings
start_celeryflower:
	RUN_ENV="prod" celery -A kubrick flower --address=127.0.0.1 --port=5555
start_celerybeat:
	RUN_ENV="prod" celery -A kubrick beat -l INFO --pidfile=/data/logs/kubrick/celerybeat.pid --logfile=/data/logs/kubrick/celerybeat.log --scheduler=django_celery_beat.schedulers:DatabaseScheduler
start_celerywork_default:
	RUN_ENV="prod" celery -A kubrick worker -l INFO -Q default -n node-default@%h --concurrency=2 --logfile=/data/logs/kubrick/celerywork_default.log
start_celerywork_timed:
	RUN_ENV="prod" celery -A kubrick worker -l INFO -Q timed -n node-timed@%h --concurrency=2 --logfile=/data/logs/kubrick/celerywork_timed.log
start_django_uwsgi:
	RUN_ENV="prod" nohup uwsgi --ini /data/workspace/kubrick/config/conf/uwsgi/uwsgi-prod.ini:django &
	sleep 5
	/opt/nginx/sbin/nginx
start_sms_receipt:
	RUN_ENV="prod" python server/corelib/third/aliyun/dayu/receipt/sms_report.py
