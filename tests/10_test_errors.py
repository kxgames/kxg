from kxg.errors import ApiUsageError
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

def test_dedent_one_line_message():
    with raises_api_usage_error() as exc:
        raise ApiUsageError('''\
                Lorem ipsum
        ''')

    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: lorem ipsum'''

def test_empty_message():
    with raises_api_usage_error() as exc:
        raise ApiUsageError('')

    assert exc.exconly() == 'kxg.errors.ApiUsageError'

def test_wrapping_no_description():
    with raises_api_usage_error() as exc:
        raise ApiUsageError('''\
Lorem ipsum dolor sit amet, consectetur adipiscing elit.''')

    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: lorem ipsum dolor sit amet,
consectetur adipiscing elit.'''
    
def test_wrapping_blank_description():
    with raises_api_usage_error() as exc:
        raise ApiUsageError('''\
Lorem ipsum dolor sit amet, consectetur adipiscing elit.

\n\n\n\n\n\n\n\n\n\n\n''')

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

def test_wrapping_indented_list():
    with raises_api_usage_error() as exc:
        raise ApiUsageError('''\
                Lorem ipsum dolor sit amet, consectetur adipiscing elit.

                Aenean at tellus ut velit dignissim tincidunt.  Curabitur 
                euismod laoreet orci semper dignissim. Suspendisse potenti. 

                1. Vivamus sed enim quis dui pulvinar pharetra.  Duis 
                   condimentum ultricies ipsum, sed ornare leo vestibulum 
                   vitae.  Sed ut justo massa, varius molestie diam. 
                
                2. Sed lacus quam, tempor in dictum sed, posuere et diam. 
                   Maecenas tincidunt enim elementum turpis blandit tempus.  
                   Nam lectus justo, adipiscing vitae ultricies egestas, porta 
                   nec diam.
                
                3. Aenean ac neque tortor.  Cras tempus lacus nec leo ultrices 
                   suscipit.  Etiam sed aliquam tortor.  Duis lacus metus, 
                   euismod ut viverra sit amet, pulvinar sed urna.''')

    print(exc.exconly())
    assert exc.exconly() == '''\
kxg.errors.ApiUsageError: lorem ipsum dolor sit amet,
consectetur adipiscing elit.

Aenean at tellus ut velit dignissim tincidunt.  Curabitur
euismod laoreet orci semper dignissim. Suspendisse potenti.

1. Vivamus sed enim quis dui pulvinar pharetra.  Duis
   condimentum ultricies ipsum, sed ornare leo vestibulum
   vitae.  Sed ut justo massa, varius molestie diam.

2. Sed lacus quam, tempor in dictum sed, posuere et diam.
   Maecenas tincidunt enim elementum turpis blandit tempus.
   Nam lectus justo, adipiscing vitae ultricies egestas, porta
   nec diam.

3. Aenean ac neque tortor.  Cras tempus lacus nec leo ultrices
   suscipit.  Etiam sed aliquam tortor.  Duis lacus metus,
   euismod ut viverra sit amet, pulvinar sed urna.'''

def test_too_many_spaces():
    # This is a real-life error message that was getting two spaces where the 
    # line wrapped, e.g. "an  id" instead of "an id".

    with raises_api_usage_error("because it doesn't have an id"):
        raise ApiUsageError("""\
                Can't add DummyToken to the world because it doesn't have an 
                id.""")

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


