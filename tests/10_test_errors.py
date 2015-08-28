import kxg
from test_helpers import *

def test_api_usage_error():
    from kxg.errors import ApiUsageError, ApiUsageErrorFactory

    ApiUsageError.message_width = 63

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


