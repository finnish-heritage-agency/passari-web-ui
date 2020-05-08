// Simple script to update the counters on the navbar
(function() {
    "use strict";

    var UPDATE_INTERVAL = 2000;  // 2 seconds

    var updateNavbar = async () => {
        // Only update stats if window is in focus
        if (document.visibilityState != "visible") {
            window.setTimeout(updateNavbar, 500);
            return;
        }

        var result = await apiFetch(URLMap['api.navbar_stats']);
        var data = await result.json();

        for (var [queueName, queueData] of Object.entries(data['queues'])) {
            var pendingElem = $(`#${queueName}_pending_counter`);
            var processingElem = $(`#${queueName}_processing_counter`);

            pendingElem.hide();
            $(processingElem).parent().hide();

            var pending = queueData["pending"];
            var processing = queueData["processing"];

            if (pending > 0) {
                pendingElem.text(pending);
                pendingElem.show();
            }

            if (processing > 0) {
                processingElem.text(processing);
                $(processingElem).parent().show();
            }
        }

        var failedElem = $("#failed_counter");
        var failed = data["failed"];
        if (failed > 0) {
            failedElem.text(failed);
            failedElem.show();
        } else {
            failedElem.hide();
        }

        // Update every 2 seconds
        window.setTimeout(updateNavbar, UPDATE_INTERVAL);
    };

    updateNavbar();
})();
