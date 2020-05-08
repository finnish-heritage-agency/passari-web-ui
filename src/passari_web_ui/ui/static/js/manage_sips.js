// Wait 0.7 second before sending a search request
var SEARCH_POLL_LAG = 700;
var OBJECTS_PER_PAGE = 20;

var app = new Vue({
    el: "#manage_sips_app",
    data: {
        searchTimeout: null,

        // Search options
        onlyLatestPackages: true,
        showPreserved: true,
        showRejected: true,
        showCancelled: false,
        showProcessing: false,
        searchQuery: "",

        // Search results
        lastPerformedSearchQuery: "",
        searchInProgress: false,
        results: [],
        resultCount: 0,
        pageNumbers: [],
        page: 1,
        pageCount: 0,

        // Modal settings
        reenqueueInProgress: false,
        packageToReenqueue: {},
        reenqueueError: "",

        MUSEUMPLUS_UI_URL: MUSEUMPLUS_UI_URL
    },
    methods: {
        searchQueryChanged: function(query) {
            if (app.searchTimeout) {
                window.clearTimeout(app.searchTimeout);
            }

            app.searchTimeout = window.setTimeout(function() {
                app.updateResults();
            }, SEARCH_POLL_LAG);
        },
        searchQueryPressed: function(evt) {
            // Perform search instantly if Enter was pressed
            if (evt.keyCode == 13) {
                app.updateResults();
            }
        },
        changePage: function(page) {
            app.page = page;
            app.updateResults();
        },
        updateResults: function() {
            updateResults();
        },
        pageItemClassForPage: (page) => {
            var itemClass = "page-item";

            if (app.page === page) {
                itemClass += " active";
            }

            if (app.searchInProgress) {
                itemClass += " disabled";
            }

            return itemClass;
        },
        viewUrlForPackage: function(package_id) {
            return URLMap["ui.manage_sips.view"].replace(
                "PACKAGE_ID", package_id
            );
        },
        openReenqueueModal: function(package) {
            app.packageToReenqueue = package;
            this.$bvModal.show("reenqueue_object_modal");
        },
        reenqueueObjectFromModal: function(evt) {
            // Prevent modal from closing
            evt.preventDefault();

            app.reenqueueInProgress = true;

            reenqueueObject(app.packageToReenqueue.object_id).then((result) => {
                app.reenqueueInProgress = false;

                this.$bvModal.hide("reenqueue_object_modal");

                if (result === true) {
                    // Re-enqueuing succeeded. Reload the list.
                    updateResults();
                } else {
                    // Re-enqueueing failed. Show the error message.
                    app.reenqueueError = result;
                    this.$bvModal.show("reenqueue_object_error_modal");
                }
            });
        }
    }
});

async function reenqueueObject(objectId) {
    data = {"object_id": objectId};

    var formData = new FormData();
    formData.append("object_id", objectId);

    var response = await apiFetch(URLMap["api.reenqueue_object"], {
        method: "POST",
        body: formData
    });
    var data = await response.json();

    if (data["success"]) {
        return true;
    } else {
        return data["error"];
    }
};

async function updateResults() {
    if (app.searchTimeout) {
        window.clearTimeout(app.searchTimeout);
    }

    app.searchInProgress = true;

    var searchQuery = app.searchQuery;
    var queryChanged = searchQuery != app.lastPerformedSearchQuery;
    if (queryChanged) {
        // If the search query was changed, reset the page to 1
        app.page = 1;
    }

    var url = new URL(URLMap["api.list_sips"]);
    url.searchParams.append("search", searchQuery);
    url.searchParams.append("page", app.page);
    url.searchParams.append("limit", OBJECTS_PER_PAGE);

    url.searchParams.append("only_latest", app.onlyLatestPackages);
    url.searchParams.append("preserved", app.showPreserved);
    url.searchParams.append("rejected", app.showRejected);
    url.searchParams.append("cancelled", app.showCancelled);
    url.searchParams.append("processing", app.showProcessing);

    var result = await apiFetch(url);
    var data = await result.json();

    app.lastPerformedSearchQuery = searchQuery;

    app.results = data["results"];
    app.resultCount = data["result_count"];
    app.pageNumbers = data["page_numbers"];
    app.page = Math.max(data["page"], 1);
    app.pageCount = data["page_count"];

    app.searchInProgress = false;

    if (app.page > app.pageCount && app.pageCount > 0) {
        // If the last page isn't actually available, set the user back
        // to the latest available page
        app.page = Math.max(app.pageCount, 1);
        updateResults();
    }
};

updateResults();
