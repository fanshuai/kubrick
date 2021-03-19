## Pyenv
    https://github.com/pyenv/pyenv


##### pyenv
    git clone https://github.com/pyenv/pyenv.git ~/.pyenv
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
    echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bashrc
    exec "$SHELL"
    source .bashrc


##### pyenv-virtualenv
    git clone https://github.com/pyenv/pyenv-virtualenv.git $(pyenv root)/plugins/pyenv-virtualenv
    echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
    exec "$SHELL"
    source .bashrc


##### pyenv-update
    git clone git://github.com/pyenv/pyenv-update.git $(pyenv root)/plugins/pyenv-update
    pyenv update


##### requirements
    sudo apt install zlibc zlib1g-dev
    sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev


##### install python
    pyenv install 3.8.2
    # pyenv uninstall 3.8.2
    # pyenv versions


##### create env
    pyenv virtualenv 3.8.2 kubrick-env-3.8.5
    # pyenv uninstall kubrick-env-3.8.5
    pyenv activate kubrick-env-3.8.5
    # pyenv deactivate


##### mkdir ~/.pip && vi ~/.pip/pip.conf
    [list]
    format=columns
    [global]
    index-url = https://mirrors.aliyun.com/pypi/simple/


##### pip use 
    pip list --outdated
    pip list --outdated --no-cache-dir
    pip install --upgrade pip --no-cache-dir
    pip install --upgrade setuptools --no-cache-dir
    pip install -r requirements.txt --upgrade --no-cache-dir


##### supervisor use
    with python
    /home/vagrant/.pyenv/versions/kubrick-env-3.8.5/bin/python
