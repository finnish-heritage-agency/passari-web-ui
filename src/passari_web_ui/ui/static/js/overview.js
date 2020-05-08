var UPDATE_INTERVAL = 4000; // 4 seconds

var app = new Vue({
    el: "#overview_app",
    data: {
        steps: {},
        totalCount: 120,
        hoveringState: null,
        stepInfoElements: [
            {
                "state": "pending",
                "title": "Pending",
                "description": (
                    "Pending objects include objects that have never been " +
                    "preserved, or modified objects that are pending a new " +
                    "preservation submission."
                )
            },
            {
                "state": "download_object",
                "title": "Download object",
                "description": (
                    "Objects that are currently being downloaded from the " +
                    "MuseumPlus service."
                )
            },
            {
                "state": "create_sip",
                "title": "Create SIP",
                "description": (
                    "Objects that are being validated and packaged into " +
                    "Submission Information Packages for submission into " +
                    "the digital preservation service."
                )
            },
            {
                "state": "submit_sip",
                "title": "Submit SIP",
                "description": (
                    "Objects that are being uploaded into the digital " +
                    "preservation service as a Submission Information Package."
                )
            },
            {
                "state": "submitted",
                "title": "Submitted",
                "description": (
                    "Objects that have been uploaded into the digital " +
                    "preservation service and and are currently being " +
                    "processed."
                )
            },
            {
                "state": "confirm_sip",
                "title": "Confirm SIP",
                "description": (
                    "Objects that have been received and processed by the " +
                    "digital preservation service. The object will be " +
                    "marked shortly as either 'rejected' or 'preserved'."
                )
            },
            {
                "state": "preserved",
                "title": "Preserved",
                "description": (
                    "Objects that have been received and accepted by the " +
                    "digital preservation service, and are up-to-date."
                )
            },
            {
                "state": "rejected",
                "title": "Rejected",
                "description": (
                    "Objects that were rejected by the digital preservation " +
                    "service."
                )
            },
            {
                "state": "frozen",
                "title": "Frozen",
                "description": (
                    "Objects that are exempt from the preservation " +
                    "workflow. For example, the file format might not be " +
                    "supported by the digital preservation service."
                )
            },
            {
                "state": "failed",
                "title": "Failed",
                "description": (
                    "Objects that triggered an error in the Passari " +
                    "workflow during one of the workflow steps."
                )
            }
        ]
    },
    computed: {
        stepsAsArray: function() {
            if (Object.keys(this.steps).length === 0) {
                return [];
            }

            var stepNames = app.stepInfoElements.map(
                (data) => { return data.state; }
            );

            // Return the different steps as an ordered array
            return stepNames.map((name) => { return this.steps[name]; });
        }
    },
    methods: {
        hoverState: function(state) {
            this.hoveringState = state;
            this.$root.$emit("bv::hide::tooltip");
            if (state !== null) {
                this.$root.$emit("bv::show::tooltip", `progress_${state}`);
            }
        }
    }
});

var updateOverview = async () => {
    // Only update stats if window is in focus
    if (document.visibilityState != "visible") {
        window.setTimeout(updateOverview, 500);
        return;
    }

    var result = await apiFetch(URLMap["api.overview_stats"]);
    var data = await result.json();

    for (let [state, entry] of Object.entries(data["steps"])) {
        Vue.set(app.steps, state, entry);
        app.steps[state]["state"] = state;
    }
    app.totalCount = data["total_count"];

    window.setTimeout(updateOverview, UPDATE_INTERVAL);
};

updateOverview();
