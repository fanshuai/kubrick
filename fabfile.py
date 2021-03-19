import click
from enum import Enum
from invoke import Responder
from fabric import Connection


kubrick_dir = '/data/workspace/kubrick'
pyenv_bin = 'RUN_ENV="prod" /home/work/.pyenv/versions/kubrick-env-3.8.5/bin'


django_manage = f"cd {kubrick_dir} && {pyenv_bin}/python manage.py"


sudopass = Responder(
    pattern=r'\[sudo\] password:',
    response='my password\n',
)


class Host(Enum):
    DaowoApi = 'daowo-api'


def disk_free(c):
    """ 获取硬盘使用 """
    uname = c.run('uname -s', hide=True)
    if 'Linux' in uname.stdout:
        command = "df -h / | tail -n1 | awk '{print $5}'"
        result = c.run(command, hide=True).stdout.strip()
        return result
    err = f"No idea how to get disk space on {uname}!"
    raise Exception(err)


def run_pipelines(pipelines):
    """ 执行 """
    from server.corelib.dealer.deal_time import get_now
    c = Connection(Host.DaowoApi.value)
    result = disk_free(c)
    print(f'=> {disk_free.__doc__}: {result}\n')
    for stage, (doc, command) in enumerate(pipelines):
        dt_start = get_now()
        time_str = dt_start.format('HH:mm:ss')
        print(f'\n\n[{time_str}] Stage {stage + 1} => {doc}:\n{command} ...\n')
        pty = str(command).startswith('sudo')
        c.run(command, pty=pty, watchers=[sudopass]).stdout.strip()
        ts_us = (get_now() - dt_start).in_seconds()
        print(f'Stage {stage + 1} use {ts_us}S')
    print('\n\nrun_pipelines done :)')


def online_deploy():
    """ 上线部署 """
    pipelines = (
        ("更新代码[kubrick]", f"cd {kubrick_dir} && git pull"),
        ("清理代码缓存[pycache]", f"cd {kubrick_dir} && find . -type d -name __pycache__ | xargs rm -fr"),
        ("升级PIP", f"cd {kubrick_dir} && {pyenv_bin}/pip install --upgrade pip --default-timeout=5"),
        ("升级依赖包", f"cd {kubrick_dir} && {pyenv_bin}/pip install --upgrade -r requirements.txt --default-timeout=5"),
        ("Django 数据模型更新", f"{django_manage} migrate"),
        ("Django 静态文件更新", f"{django_manage} collectstatic --noinput"),
        ("DjangoCache 清理", f"{django_manage} clearcache --alias=default,session"),
        ("DjangoSession 清理", f"{django_manage} clearsessions"),
        ("Supervisor 配置", f"cp -R {kubrick_dir}/config/conf/supervisor/conf.d/*-prod.conf /data/supervisor/conf.d/"),
        ("Supervisor Reread", f"cd /data/supervisor && {pyenv_bin}/supervisorctl reread"),
        ("Supervisor Update", f"cd /data/supervisor && {pyenv_bin}/supervisorctl update"),
        ("Restart kubrick_api", f"cd /data/supervisor && {pyenv_bin}/supervisorctl restart kubrick_api"),
        ("Restart celerybeat", f"cd /data/supervisor && {pyenv_bin}/supervisorctl restart celerybeat"),
        ("Restart celerywork_timed", f"cd /data/supervisor && {pyenv_bin}/supervisorctl restart celerywork_timed"),
        ("Restart celerywork_default", f"cd /data/supervisor && {pyenv_bin}/supervisorctl restart celerywork_default"),
        ("Restart sms_report", f"cd /data/supervisor && {pyenv_bin}/supervisorctl restart sms_report:*"),
        ("Restart kubrick_djadmin", f"cd /data/supervisor && {pyenv_bin}/supervisorctl restart kubrick_djadmin"),
        ("Restart kubrick_qrimage", f"cd /data/supervisor && {pyenv_bin}/supervisorctl restart kubrick_qrimage"),
        ("Supervisor Status", f"cd /data/supervisor && {pyenv_bin}/supervisorctl status"),
        ("DjangoSilk 临时文件清理", f"rm -f /data/logs/kubrick-silky/*.prof"),
        ("DjangoSilk 日志清理", f"{django_manage} silk_clear_request_log"),
    )
    run_pipelines(pipelines)
    print('\n\nonline_deploy done :)')


def nginx_reload():
    """ Nginx 重启 """
    pipelines = (
        ("Nginx配置更新", f"cp {kubrick_dir}/config/conf/nginx/conf.d/* /etc/nginx/conf.d/"),
        ("Nginx配置检查", f"sudo nginx -t"),
        ("Nginx重启", f"sudo nginx -s reload"),
    )
    run_pipelines(pipelines)
    print('\n\nnginx_reload done :)')


def letsencrypt_renew():
    """ 证书更新 """
    c = Connection(Host.Capital.value)
    pipelines = (
        ("更新证书", f"sudo certbot renew"),
        ("Nginx配置检查", f"sudo nginx -t"),
        ("Nginx重启", f"sudo nginx -s reload"),
    )
    for stage, (doc, command) in enumerate(pipelines):
        print(f'\nStage {stage + 1} => {doc} ...')
        pty = str(command).startswith('sudo')
        c.run(command, pty=pty, watchers=[sudopass]).stdout.strip()
    print('\n\nletsencrypt_renew done :)')


@click.command()
@click.option(
    '--action', prompt='要执行的操作',
    help='nginx / deploy / renew'
)
def main(action):
    funcs = {
        'nginx': nginx_reload,
        'deploy': online_deploy,
        'renew': letsencrypt_renew,
    }
    function = funcs.get(action)
    if not callable(function):
        print(f'操作[{action}]不存在！！')
        return
    doc = function.__doc__
    print(f'{doc} 开始...')
    function()
    print(f'{doc} 完成。')


if __name__ == '__main__':
    main()
