# **DEPRECATED - please consider using  [popolo-name-resolver](https://github.com/mysociety/popolo-name-resolver**)

popit-resolver
==============


A project to resolve people's names to a Popit record (see
<http://mysociety.github.com/popit-resolver/>)

Documentation
-------------
Documentation (a work in progress) can be found at: https://github.com/mysociety/popit-resolver

Installation
------------

Something like the following, customised to your particular environment or set up:

    # Clone the repo
    mkdir popit_resolver
    cd popit_resolver
    git clone https://github.com/mysociety/popit-resolver.git

    cd popit_resolver

    # Install the required software packages
    Assuming you're on a debian/ubuntu server:
    grep -v '#' conf/packages | sudo xargs apt-get install -y

    # Create a postgres database and user
    sudo -u postgres psql
    postgres=# CREATE USER resolver WITH password 'resolver';
    CREATE ROLE
    postgres=# CREATE DATABASE resolver WITH OWNER resolver;
    CREATE DATABASE

    # Set up a python virtual environment, activate it
    # this assumes that you will set up the virtualenv in ..
    # (e.g. outside the repo.
    #  You can use ~/.virtualenvs/ etc. if you prefer)
    virtualenv --no-site-packages ../virtualenv-resolver
    source ../virtualenv-resolver/bin/activate

    # Install required python packages
    pip install --requirement requirements.txt

    cp conf/general.yml-example conf/general.yml
    # Alter conf/general.yml as per your set up
    #    use the 'resolver' account as above for POPIT_RESOLVER_DB_{USER,NAME,PASS}
    #
    # For *development* use only:
    #    use recommendations for BASE_{HOST,PORT}
    #    DJANGO_SECRET_KEY isn't needed

    # Set up database
    ./manage.py syncdb

    # This will ask you if you wish to create a Django superuser, which you'll
    # use to access the POPIT_RESOLVER admin interface. You can always do it later with
    # ./manage.py createsuperuser, but there's no harm in doing it now either,
    # just remember the details you choose!

    ./manage.py migrate

    # gather all the static files in one place
    ./manage.py collectstatic --noinput

Testing
-------

    ./manage.py test
