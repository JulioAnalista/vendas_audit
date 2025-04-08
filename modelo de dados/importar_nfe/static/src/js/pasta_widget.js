odoo.define('importar_nfe.pasta_widget', function (require) {
    "use strict";

    var core = require('web.core');
    var FieldChar = require('web.basic_fields').FieldChar;
    var field_registry = require('web.field_registry');

    var PastaWidget = FieldChar.extend({
        template: 'importar_nfe.pasta_widget',
        events: {
            'click .o_pasta_button': '_onClickPastaButton',
        },

        _onClickPastaButton: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            
            var input = document.createElement('input');
            input.type = 'file';
            input.webkitdirectory = true;
            input.directory = true;
            
            input.onchange = function(e) {
                if (e.target.files && e.target.files.length > 0) {
                    var path = e.target.files[0].webkitRelativePath;
                    var folder = path.split('/')[0];
                    this._setValue(folder);
                }
            }.bind(this);
            
            input.click();
        },
    });

    field_registry.add('pasta_widget', PastaWidget);

    return PastaWidget;
}); 