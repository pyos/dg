$(function () {
  $("#repl-doit").click(function () {
    var self  = this;
    var code  = $("#repl-code")  .val();
    var stdin = $("#repl-stdin") .val();

    if ($(self).hasClass("disabled")) return;
    $(self)           .addClass("disabled");
    $("#repl-error")  .hide();
    $("#repl-status") .hide();
    $("#repl-waiting").show();

    $.ajax({
      url: 'http://127.0.0.1:8000/',
      type: 'POST',
      data: {'code': code, 'stdin': stdin},
      dataType: 'json',

      success: function (data) {
        $(self)           .removeClass ("disabled");
        $("#repl-status") .show();
        $("#repl-waiting").hide();
        $("#repl-retval") .text(data.status);
        $("#repl-signal") .text(data.signal);
        $("#repl-time")   .text(Math.round(data.time * 1000) / 1000);
        $("#repl-stdout") .text(data.stdout);
        $("#repl-stderr") .text(data.stderr);
        if (data.stdout !== "") $("#repl-stdout-wrap").show(); else $("#repl-stdout-wrap").hide();
        if (data.stderr !== "") $("#repl-stderr-wrap").show(); else $("#repl-stderr-wrap").hide();

        if (data.signal) { $("#repl-signal-wrap").show(); $("#repl-retval-wrap").hide(); }
        else             { $("#repl-signal-wrap").hide(); $("#repl-retval-wrap").show(); }

        if      (data.signal != 0) $("#repl-status-sum").text("Killed");
        else if (data.status != 0) $("#repl-status-sum").text("Runtime error");
        else                       $("#repl-status-sum").text("Finished");
      },

      error: function (data) {
        console.log(data.responseJSON.error);
        $(self)             .removeClass ("disabled");
        $("#repl-error")    .show();
        $("#repl-waiting")  .hide();
        $("#repl-error-msg").text(data.responseJSON.error)
      }
    });
  });
});
