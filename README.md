skytap-api
==========
skytapAPI is a pythonic implementation of a [Facade pattern](en.wikipedia.org/wiki/Facade_pattern) for the [Skytap Rest API](help.skytap.com/#api-documentation).

Requirements
------------
* Python 3.4+
* [requests](http://docs.python-requests.org/en/latest/)

Using skytapAPI
---------------
#### Example

```python
# Get a specific Skytap user
import skytapAPI

skytap = skytapAPI.SkytapAPI('https://cloud.skytap.com', 'login@example.com',
                         'someskytapapikey')
user = skytap.get_user('12345')
print(user['email'])
```

