;(function($) {

    var disable_submits = function() {
        return $('input[type="submit"]').attr('disabled', 'disabled');
    }

    var enable_submits = function() {
        return $('input[type="submit"]').removeAttr('disabled');
    }


    var do_ajax_success = function(data, textStatus, jqXHR) {
        var callback = enable_submits;
        // in the event there were no missing items to add, the server returns
        // 202 so that we can avoid re-enabling the save button for no reason.
        // Any other 2xx code means the server didn't error and there are
        // URLs to process.
        if (jqXHR.status !== void(0) && jqXHR.status === 202) {
            callback = disable_submits;
        }
        $('.menuhin_preview').html(data).fadeIn(500, callback);
    };

    var do_ajax_error = function(data, textStatus, jqXHR) {
        var preview_html = $('.menuhin_preview');
        if (data !== void(0) && data.status !== void(0)) {
            if (data.status === 403 && data.responseText) {
                preview_html.html('<p>' + data.responseText.toString() + '</p>');
            } else {
                preview_html.html('<p>An error occurred</p>');
            }
        };
        preview_html.fadeIn(250, enable_submits);
    };

    var do_ajax = function(evt) {
        var self;
        var form;
        var klass_errors;

        klass_errors = $('.field-klass .errorlist');

        disable_submits.call(this);

        self = $(this);
        if ($.trim(self.val()) !== '') {
            $('.menuhin_preview').hide();
            klass_errors.slideUp();
            form = $(this.form);
            $.ajax({
                url: form.attr('action'),
                data: form.serialize(),
                type: 'POST',
                success: do_ajax_success,
                error: do_ajax_error,
                cache: false
            });
        } else {
            $('.menuhin_preview').hide();
            if (klass_errors.length > 0) {
                klass_errors.show();
            }
            do_ajax_error.call(this, {
                status: 403,
                responseText: 'Select a valid choice to preview URL additions.'
            });
        }
    };

    var setup = function() {
        $('#id_klass').bind('change', do_ajax);
        $('form').bind('submit', disable_submits);
    };
    $(document).ready(setup);
})(django.jQuery);
