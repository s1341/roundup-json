//------------------------------------------------------------------------------
// selectization
//------------------------------------------------------------------------------
// build a selectized input from a few key options:
function attach_selectize(id, options)
{
    var defaults = {
        columns: "id,name,description",
        value_field: "name",
        label_field: "name",
        search_field: "name",
        description_field: "description",
        create: false,
        filterspec: null,
        filters: "",
        on_load: null,
    };
    options = $.extend({},defaults, options);


    if (options.filterspec) {
        options.filters = "&@filter=" + Object.keys(options.filterspec);
        for (var f in options.filterspec) {
            if (options.filterspec[f]) {
                options.filters += '&' + f + '=' + options.filterspec[f];
            }
        }
    }
    res = $(id).selectize({
        delimiter: ',',
        valueField: options.value_field,
        labelField: options.label_field,
        searchField: options.search_field,
        create: options.create,
        persist: false,
        preload: true,
        render: {
            option: function(item, escape) {
                return "<div>" +
                    "<span class='select_item_title'><span class='select_item_name'>" + escape(item[options.label_field]) + "</span></span>" +
                    "<span class='select_item_description'>" + (item[options.description_field] ? escape(item[options.description_field]) : "") + "</span>" +

                    "</div>";
            }
        },
        load: function(query, callback) {
            $.ajax({
                url: options.data_class + '?@action=get_json&@columns=' + options.columns + options.filters,
                type: 'GET',
                error: function() {
                    console.log("ajax error in get_json for selectized id:", id);
                    callback();
                },
                success: function(res) {
                    callback(res);
                }
            });
        },
    })[0].selectize;
    if (options.on_load)
        res.on("load", options.on_load);
    return res;
}
