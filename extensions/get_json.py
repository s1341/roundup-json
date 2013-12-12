from roundup.cgi.actions import Action
from roundup.cgi import exceptions, templating
import cgi
import roundup
import json
import re
from pprint import pprint


def _walkprop(db, node, path):
    n = node
    for p in path.split("."):
        i = n.get(p)

        if p in ['creator']:
            p = 'user'
        n = db.getnode(p, i)
    return n


class GetJSONAction(Action):
    name = 'export'
    permissionType = 'View'

    def _safe_request_lookup(self, name, default=None, cast=None):
        if name in self.request.form:
            val = self.request.form[name].value
            if cast:
                return cast(val)
            return val
        return default

    def handle(self):
        """ Export the specified search query as JSON. """
        # figure the request
        self.request = templating.HTMLRequest(self.client)
        try:
            json_nested = self._safe_request_lookup("json_nested", False, cast=bool)
            itemclass = self._safe_request_lookup("itemclass", self.request.classname, cast=str)
            json_flat_array = self._safe_request_lookup("json_flat_array", False, cast=bool)

            self.columns = {}
            for i, c in enumerate(self.request.columns):
                self.columns[c] = ColumnDescriptor(c, c, i)

            res = self._retrieve_data(itemclass, self.columns.values(), json_nested, self.request.search_text, self.request.filterspec, self.request.sort, self.request.group)
            res = res[0]

            if json_flat_array:
                if len(self.request.columns) > 1:
                    return "ERROR: only one column is allowed when flattening to an array"
                r = []
                for i in res:
                    for k, v in i.items():
                        r.append(v)
                res = r

            if self.client.env['REQUEST_METHOD'] == 'HEAD':
                # all done, return a dummy string
                return 'dummy'
            res = json.dumps(res)
        except:
            self._set_headers("text/html")
            raise
        finally:
            self._set_headers()
        return res

    def _set_headers(self, mimetype='applicaton/json; charset=utf-8'):
        self.client.additional_headers['Content-Type'] = mimetype
        self.client.header()

    def _retrieve_data(self, itemclass, columns, json_nested=False, searchtext=None, filterspec=[], sort=[], group=[]):
        klass = self.db.getclass(itemclass)

        # check if all columns exist on class
        # the exception must be raised before sending header
        props = klass.getprops()
        for cname in columns:
            if not type(cname) is str:
                cname = cname.get_name()
            # TODO ? custom handling of project and device_type, because we need to walk up
            # the tree a little.
            if cname not in props and "." not in cname:
                # TODO raise exceptions.NotFound(.....) does not give message
                # so using SeriousError instead
                self.client.response_code = 404
                raise exceptions.SeriousError(
                    self._('Column "%(column)s" not fo und on %(class)s')
                    % {'column': cgi.escape(cname), 'class': itemclass})

        # full-text search
        # TODO: currently only matches FULL words. This is how roundup implements search.
        matches = None
        if searchtext:
            """matches = self.client.db.indexer.search(
                [w.upper().encode("utf-8", "replace") for w in re.findall(
                    r'(?u)\b\w{2,25}\b',
                    unicode(searchtext, "utf-8", "replace")
                )], klass)

            """
            matches = self.db.indexer.search(
                re.findall(r'\b\w{2,25}\b', searchtext), klass)

        # json_flat is currently broken, always use nested
        if 1 or json_nested:
            obj = self._build_json_nested(klass, columns, klass.filter(matches, filterspec, sort, group))
        else:
            obj = self._build_json_flat(klass, columns, klass.filter(matches, filterspec, sort, group))

        return obj, len(obj), klass.count()

    # this is currently broken!
    def _build_json_flat(self, klass, columns, itemidlist):
        res = []
        for itemid in itemidlist:
            row = {}
            for col in columns:
                name = col.get_name()
                if "." in name:
                    path, d, prop = name.rpartition(".")
                    l = self._walkprop(klass.getnode(itemid), path)
                    row[self.replace_dots_with_dashes and name.replace('.', '-') or name] = l[prop]
                    continue
                row[name] = klass.get(itemid, name)
                if row[name] and isinstance(row[name], roundup.date.Date):
                    row[name] = row[name].formal()
            res.append(row)
        return res

    def _build_tree(self, root, name, node):
        valid_classes = self.db.getclasses()
        tree = root
        fk = None
        for component in name.split('.'):
            if not node:
                # missing foreign key, but still complete the component walk
                # so we get the full transitive tree
                tree[component] = None
                continue
            if component == "id" and fk:
                # we will add a 'fake' id atttribute with the fk of the node itself
                tree[component] = fk
            elif not component in node.keys():
                # TODO: throw a more useful error
                raise Exception("%s is not available on %s" % (component, node))
            fk = node.get(component)
            if not component in tree:
                tree[component] = {}

            if component in ['creator']:
                mapped_component = 'user'
            else:
                mapped_component = component

            if fk is None:
                # there is no foreign key. This is basically a broken reference.
                # for example, if no status is specified on a finding.
                node = None
            elif mapped_component in valid_classes:
                # deal with link
                # TODO: deal with multilinks (created an array in tree?)
                node = self.db.getnode(mapped_component, fk)
            elif component in node:
                # deal with properties:
                tree[component] = node[component]
            else:
                print "WTF!"
                print node
            tree = tree[component]
        return tree

    def _get_project_for_row(self, klass, itemid):
        if klass.classname in ["finding", "antifinding"]:
            path = "version.device_type.project"
        elif klass.classname == "version":
            path = "device_type.project"
        elif klass.classname == "device_type":
            path = "project"
        else:
            return None
        return _walkprop(self.db, klass.getnode(itemid), path)

    def _build_json_nested(self, klass, columns, itemidlist):
        res = []

        for itemid in itemidlist:
            row = {}
            for col in columns:
                pprint(col)
                # deal with transverse
                col_name = col.get_name()
                if "." in col_name:
                    self._build_tree(row, col_name, klass.getnode(itemid))
                    continue

                item = klass.get(itemid, col_name)
                if col_name == "proj_id" and item:
                    project = self._get_project_for_row(klass, itemid)
                    item = "%s%03d" % (project["prefix"], int(item))
                row[col_name] = item
                # special case date:
                if item and isinstance(item, roundup.date.Date):
                    row[col_name] = item.formal()
            res.append(row)
        return res


class ColumnDescriptor:
    def __init__(self, name, db_path, index, sortable=True, searchable=True, search_text=None):
        self.name, self.db_path, self.index, self.sortable, self.searchable, self.search_text = name, db_path, index, sortable, searchable, search_text
        self.is_sorting = False
        self.is_searching = self.searchable and self.search_text
        self.direction = "asc"

    def __repr__(self):
        return "<col_name: %s, db_path: %s, index: %i, sortable: %s, direction: %s>" % (self.name, self.db_path, self.index, self.sortable, self.direction)

    def get_sortattr(self):
        if self.sortable and self.is_sorting:
            return (("-" if self.direction == "desc" else "+"), self.db_path)
        return None

    def get_filterspec(self):
        if self.searchable and self.is_searching:
            return {self.db_path: self.search_text}
        return None

    def get_name(self):
        return self.db_path


class GetJSONForDataTablesAction(GetJSONAction):

    def _parse_client_columns(self):
        columns = self._safe_request_lookup("sColumns", "")
        # TODO: what do we do when there is no client side column?
        for i, col_name in enumerate([c.strip() for c in columns.split(",")]):
            self.columns[i] = ColumnDescriptor(
                col_name,
                self._safe_request_lookup('mDataProp_%d' % i),
                i,
                self._safe_request_lookup('bSortable_%d' % i, True, cast=bool),
                self._safe_request_lookup('bSearchable_%d' % i, True, cast=bool),
                self._safe_request_lookup('sSearch_%d' % i, None, cast=str),
            )
        self.client_columns = [c.strip() for c in columns.split(',')]
        self.num_client_columns = self._safe_request_lookup("iColumns", 0, cast=int)
        num_sort_cols = self._safe_request_lookup("iSortingCols", cast=int)
        if num_sort_cols:
            for i in range(num_sort_cols):
                col_index = self._safe_request_lookup('iSortCol_%d' % i, None, cast=int)
                self.columns[col_index].is_sorting = True
                self.columns[col_index].direction = self._safe_request_lookup('sSortDir_%d' % i, "asc")

    def _num_columns(self):
        return self.num_client_columns

    def _lookup_client_column(self, name):
        return self.client_columns.index(name)

    def handle(self):
        self.columns = {}
        res = ""
        mimetype = "application/json; charset=%s" % self.client.charset
        try:
            self.request = templating.HTMLRequest(self.client)

            # get parameters
            itemclass = self._safe_request_lookup("itemclass", self.request.classname, cast=str)
            json_nested = self._safe_request_lookup("json_nested", False, cast=bool)
            start = self._safe_request_lookup("iDisplayStart", self.request.startwith, cast=int)
            pagesize = self._safe_request_lookup("iDisplayLength", self.request.pagesize, cast=int)
            searchtext = self._safe_request_lookup("sSearch", self.request.search_text)

            self._parse_client_columns()
            pprint(self.columns)

            roundup_sortlist = []
            roundup_filterspec = {}  # TODO: incorporate request filterspec
            for c in self.columns.values():
                sortattr = c.get_sortattr()
                filterspec = c.get_filterspec()
                if sortattr:
                    roundup_sortlist.append(sortattr)
                if filterspec:
                    roundup_filterspec.update(filterspec)

            obj, num_items_selected, total_items = self._retrieve_data(itemclass, self.columns.values(), json_nested, searchtext, roundup_filterspec, roundup_sortlist, self.request.group)

            obj = obj[start:start + pagesize]

            sEcho = self.request.form['sEcho'].value if 'sEcho' in self.request.form else 0
            response = {
                "iTotalDisplayRecords": num_items_selected,
                "iTotalRecords": total_items,
                "sEcho": sEcho,
                "aaData": obj,
            }
            res = json.dumps(response)

        except:
            self._set_headers("text/html")
            raise

        self._set_headers(mimetype)
        return res


def init(instance):
    instance.registerAction('get_json', GetJSONAction)
    instance.registerAction('get_json_for_datatables', GetJSONForDataTablesAction)
