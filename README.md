## Kubrick (库布里克)

### 用户服务平台服务端

### Services Port
1. Web api: http://vagrant:5566
2. QR page: http://vagrant:5577
3. Django admin: http://vagrant:5588

### Migrate
> python manage.py migrate

### 服务启动
> python manage.py runserver 0.0.0.0:5566
> python manage.py collectstatic --noinput
> python manage.py runserver 0.0.0.0:5577 --settings=kubrick.qrimage.settings
> python manage.py runserver 0.0.0.0:5588 --settings=kubrick.djadmin.settings


### 接口文档
> http://vagrant:5588/docs
>
> http://vagrant:5588/swagger



###### 产品定位：扫码通话 
