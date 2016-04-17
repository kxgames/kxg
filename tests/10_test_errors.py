from kxg.errors import ApiUsageError, ApiUsageErrorFactory
from test_helpers import *

# Pytest adds a margin to exception message, so we have to make the messages a 
# little narrower than usual to fit within 80 characters during testing.  Note 
# that this setting persists throughout all the tests.
ApiUsageError.message_width = 63

def test_one_line_message():
    with raises_api_usage_error() as exc:
        raise ApiUsageError('Lorem ipsum')

    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: lorem ipsum'''

def test_wrapping_no_description():
    with raises_api_usage_error() as exc:
        raise ApiUsageError('''\
Lorem ipsum dolor sit amet, consectetur adipiscing elit.''')

    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: lorem ipsum dolor sit amet,
consectetur adipiscing elit.'''
    
def test_wrapping_short_description():
    with raises_api_usage_error() as exc:
        raise ApiUsageError('''\
Lorem ipsum dolor sit amet, consectetur adipiscing elit.

Nam justo sem, malesuada ut ultricies ac.''')

    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: lorem ipsum dolor sit amet,
consectetur adipiscing elit.

Nam justo sem, malesuada ut ultricies ac.'''

def test_wrapping_long_description():
    with raises_api_usage_error() as exc:
        raise ApiUsageError('''\
Lorem ipsum dolor sit amet, consectetur adipiscing elit.

Aenean at tellus ut velit dignissim tincidunt. Curabitur euismod laoreet orci 
semper dignissim. Suspendisse potenti. Vivamus sed enim quis dui pulvinar 
pharetra. Duis condimentum ultricies ipsum, sed ornare leo vestibulum vitae.  
Sed ut justo massa, varius molestie diam. Sed lacus quam, tempor in dictum sed, 
posuere et diam. Maecenas tincidunt enim elementum turpis blandit tempus. Nam 
lectus justo, adipiscing vitae ultricies egestas, porta nec diam. Aenean ac 
neque tortor. Cras tempus lacus nec leo ultrices suscipit. Etiam sed aliquam 
tortor. Duis lacus metus, euismod ut viverra sit amet, pulvinar sed urna.''')

    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: lorem ipsum dolor sit amet,
consectetur adipiscing elit.

Aenean at tellus ut velit dignissim tincidunt. Curabitur
euismod laoreet orci semper dignissim. Suspendisse potenti.
Vivamus sed enim quis dui pulvinar pharetra. Duis condimentum
ultricies ipsum, sed ornare leo vestibulum vitae.  Sed ut justo
massa, varius molestie diam. Sed lacus quam, tempor in dictum
sed, posuere et diam. Maecenas tincidunt enim elementum turpis
blandit tempus. Nam lectus justo, adipiscing vitae ultricies
egestas, porta nec diam. Aenean ac neque tortor. Cras tempus
lacus nec leo ultrices suscipit. Etiam sed aliquam tortor. Duis
lacus metus, euismod ut viverra sit amet, pulvinar sed urna.''' 

def test_formating_with_args():
    with raises_api_usage_error() as exc:
        raise ApiUsageError('{} {}', 'Lorem', 'ipsum')

    # Note that "Lorem" is capitalized because the braces cause it to be 
    # treated as an identifier.
    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: Lorem ipsum'''

def test_formating_with_kwargs():
    with raises_api_usage_error() as exc:
        raise ApiUsageError('{lorem} {ipsum}', lorem='Lorem', ipsum='ipsum')

    # Note that "Lorem" is capitalized because the braces cause it to be 
    # treated as an identifier.
    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: Lorem ipsum'''

def test_formatting_with_local_variables():
    lorem, ipsum = 'Lorem', 'ipsum'
    with raises_api_usage_error() as exc:
        raise ApiUsageError('{lorem} {ipsum}')

    # Note that "Lorem" is capitalized because the braces cause it to be 
    # treated as an identifier.
    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: Lorem ipsum'''

def test_api_usage_error_factory():

    class ErrorWithAttribute (ApiUsageErrorFactory):
        message = '{label}: {percent:0.2f}%'

        def __init__(self, label, percent):
            self.label = label
            self.percent = percent

    class ErrorWithNoDescription (ApiUsageErrorFactory):
        message = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.'

    class ErrorWithShortDescription (ApiUsageErrorFactory):
        message = '''\
Lorem ipsum dolor sit amet, consectetur adipiscing elit.

Nam justo sem, malesuada ut ultricies ac.'''

    class ErrorWithLongDescription (ApiUsageErrorFactory):
        message = '''\
Lorem ipsum dolor sit amet, consectetur adipiscing elit.

Aenean at tellus ut velit dignissim tincidunt. Curabitur euismod laoreet orci 
semper dignissim. Suspendisse potenti. Vivamus sed enim quis dui pulvinar 
pharetra. Duis condimentum ultricies ipsum, sed ornare leo vestibulum vitae.  
Sed ut justo massa, varius molestie diam. Sed lacus quam, tempor in dictum sed, 
posuere et diam. Maecenas tincidunt enim elementum turpis blandit tempus. Nam 
lectus justo, adipiscing vitae ultricies egestas, porta nec diam. Aenean ac 
neque tortor. Cras tempus lacus nec leo ultrices suscipit. Etiam sed aliquam 
tortor. Duis lacus metus, euismod ut viverra sit amet, pulvinar sed urna.''' 


    with raises_api_usage_error() as exc:
        raise ErrorWithAttribute('Lorem ipsum', 100 / 3)

    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: Lorem ipsum: 33.33%'''

    with raises_api_usage_error() as exc:
        raise ErrorWithNoDescription()

    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: lorem ipsum dolor sit amet,
consectetur adipiscing elit.'''
    
    with raises_api_usage_error() as exc:
        raise ErrorWithShortDescription()

    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: lorem ipsum dolor sit amet,
consectetur adipiscing elit.

Nam justo sem, malesuada ut ultricies ac.'''

    with raises_api_usage_error() as exc:
        raise ErrorWithLongDescription()

    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: lorem ipsum dolor sit amet,
consectetur adipiscing elit.

Aenean at tellus ut velit dignissim tincidunt. Curabitur
euismod laoreet orci semper dignissim. Suspendisse potenti.
Vivamus sed enim quis dui pulvinar pharetra. Duis condimentum
ultricies ipsum, sed ornare leo vestibulum vitae.  Sed ut justo
massa, varius molestie diam. Sed lacus quam, tempor in dictum
sed, posuere et diam. Maecenas tincidunt enim elementum turpis
blandit tempus. Nam lectus justo, adipiscing vitae ultricies
egestas, porta nec diam. Aenean ac neque tortor. Cras tempus
lacus nec leo ultrices suscipit. Etiam sed aliquam tortor. Duis
lacus metus, euismod ut viverra sit amet, pulvinar sed urna.''' 


