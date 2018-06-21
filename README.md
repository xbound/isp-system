# ISP system in Django

### Description

The purpose of this project was to create demo web application for ISP company. Project needed to implement most common UML types of inheritance such as disjoint inheritance, multiinheritance, dynamic inheriatnce and multiaspect type of inheritance and most common types of associations with different multiplicities, for example association one-to-one, one-to-many, many-to-one, composition and aggregation.

__Analytical diagram:__

![](https://github.com/xbound/isp-system/blob/master/cd_concept.svg) 

__Implementation diagram:__

![](https://github.com/xbound/isp-system/blob/master/cd_implementation.svg) 

### Requirements

* __Python 3__
* __virtualenv__
* __pip__
* Dependencies from `requirements.txt`

### Setup 

Clone project:
```shell
$ git clone https://github.com/xbound/isp-system
```

Create virtual environment and activate it:
```shell
$ virtualenv venv --python python3
$ source venv/bin/activate
```
Install dependencies from `requirements.txt`
```shell
$ pip install -r requirements.txt
```
Apply migrations for database:
```shell
python manage.py migrate
```
Run tests:
```shell
python manage.py test
```
Run server and navigate to [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin). You will need to create and admin user to log in.
```shell
python manage.py createsuperuser
```
