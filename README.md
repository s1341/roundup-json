roundup-json
============

JSON extensions for roundup tracker

This is a simple extension for roundup which provides useful JSON actions to
retrieve data from the server for the purposes of AJAX.

The extensions/get_json.py file implements two new actions:

### get_json
This action lets you retrieve JSON for the specified class. For example:
```
items?@action=get_json@columns=id,title,description
```
will return an array of dicts, each with id, title and description elements.

The following options are supported:

#### json_nested
NOTE: Currently json_flat is broken. json_nested is always used!

Set this option to True if you want the response to contain nested dictionaries for transverse properties.
In other words, if request the `id, name, status.name` columns you will get the following without json_nested:
```
[
  {
    'id': 1,
    'name': 'entry 1',
    'status.name': 'open'
  },
  ...
]
```
With json_nested set, the output will look like this:
```
[
  {
    'id': 1,
    'name': 'entry 1',
    'status': {
      'name': 'open'
    }
  },
  ...
]
```

#### json_flat_array
Set this option to True if you want a flat array of values from a single column only.

### get_json_for_datatables
This is a version of get_json which is specifically geared towards handling
AJAX load requests from the excellent http://http://datatables.net/ jQuery
plugin.

It uses the 'native' datatables query parameters to generate a JSON result in the format
expected by datatables.

JS helper functions
-------------------
In static/js there are two helper functions which demonstrate how to use the
get_json and get_json_for_datatables actions for two popular use-cases.

They're provided as is, and probably won't suit every use-case. I just ripped them
out of my current tracker. If you have modifications, please feel free to PR.

### generate_datatable
The generate_datatable function takes a selector for a table element and a columns
object and generates the required table and instantiates it with datatable().

### attach_selectize
The attach_selectize function takes a selector for an input and instantiates it with
the http://brianreavis.github.io/selectize.js/ plugin.

See the examples.html file for rough examples of how to use these helper functions.
Again, these examples are more for instructional purposes. They will not work as is.
Use them as a template in your own roundup html pages.
