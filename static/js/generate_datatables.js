/*
 * Tools for generating datatables.net tables with ease.
 */
function build_query (base, args) {
    var res = base + "?";
    for (var i in args) {
        res += i + "=" + args[i] + "&";
    }
    return res.slice(0, -1);
}

//------------------------------------------------------------------------------
// datatables
//------------------------------------------------------------------------------
function generate_datatable(tableselector, itemclass, columns, filterspec, options) {
    var column_list = "";
    var table = $(tableselector);
    var defaults = {
        showFilterFooters : true,
        showTableTools : true,
        showSearch: true,
        showPager: true,
        showInfo: true,
        destroy: false,
        on_load: null,
        no_ajax: false,
        data_array: null, // should always be set if no_ajax is
    };
    options = $.extend({}, defaults, options);

    table.empty();
    var thead = table.append("<thead><tr></tr></thead>").find("thead:first tr");
    var tfoot = table.append("<tfoot><tr></tr></tfoot>").find("tfoot:first tr");

    if(typeof columns === "string") {
        //TODO: This is a truly horrible idea! eval-ing the columns might lead to all
        //kinds of potential security issues. Consider finding a less horrific way to
        //deal with this case (or just don't allow strings altogether?)
        columns = eval(columns);
    }

    for (var i = 0; i < columns.length; i++)
    {
        c = columns[i];
        column_list += c.mData + ",";
        visible = true;
        if ('bVisible' in c)
            visible = c.bVisible;

        column_name = c.mData;
        if ('sName' in c)
        {
            column_name = c.sName;
        }

        // create headers and footers
        thead.append("<th>" + column_name + "</th>");
        if (options.showFilterFooters)
            tfoot.append("<th><input class='search_init' type='text' name='search_" + column_name + "' placeholder='Search " + column_name + "' data-for-colno='" + i +"'></th>");

    }

    column_list = column_list.slice(0,-1);
    var sDom = (options.showTableTools ? 'T' : '') + (options.showSearch ? 'f' : '') + 'rt' + (options.showInfo ? 'i' : '') + (options.showPager ? 'lp' : '');

    if (! options.no_ajax) {
        var query_args = {
            "@action": "get_json_for_datatables",
            "json_nested": "yes",
            "@columns": column_list,
            "@filterspec": filterspec ? filterspec : "",
        };
        table.dataTable( {
            sDom: sDom,
            oTableTools: {
                sSwfPath: "@@file/datatables-tabletools/media/swf/copy_csv_xls_pdf.swf",
            },
            bServerSide: true,
            bProcessing: true,
            aoColumns: columns,
            sAjaxSource: build_query(itemclass, query_args),
            fnInitComplete: options.on_load ? function (oSettings, json) { options.on_load(); } : null,
            iDisplayLength: 50,
            bDestroy: true, //if there was an existing table, destroy it
            bDestroy: options.destroy, //FIXME: Why is this duplicated?
        });
    } else {
        table.dataTable( {
            sDom: sDom,
            oTableTools: {
                sSwfPath: "@@file/datatables-tabletools/media/swf/copy_csv_xls_pdf.swf",
            },
            aoColumns: columns,
            aaData: options.data_array,
            fnInitComplete: options.on_load ? function (oSettings, json) { options.on_load(); } : null,
            iDisplayLength: 50,
            //bDestroy: true, //if there was an existing table, destroy it
            //bDestroy: options.destroy,
        });
    }

    //generate a filter box for each column

    if (options.showFilterFooters) {
        table.find("tfoot input").keyup( function () {
            /* Filter on the column (there index) of this element */
            table.fnFilter( this.value, $(this).data("for-colno"));
        });
    }
}
