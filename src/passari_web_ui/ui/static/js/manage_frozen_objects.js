// Wait 0.7 second before sending a search request
var SEARCH_POLL_LAG = 700;
var OBJECTS_PER_PAGE = 20;

var app = new Vue({
    el: "#manage_frozen_objects_app",
    data: {
        // Search
        searchTimeout: null,
        searchQuery: "",
        lastPerformedSearchQuery: "",
        searchInProgress: false,
        results: [],
        resultCount: 0,
        pageNumbers: [],
        page: 1,
        pageCount: 0,

        // Unfreeze modal
        unfreezeInProgress: false,
        unfreezeReason: null,
        enqueueUnfrozenObject: false,
        objectIdToUnfreeze: null,

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
        openUnfreezeModal: function(objectId, reason) {
            app.enqueueUnfrozenObject = false;
            app.objectIdToUnfreeze = objectId;
            app.unfreezeReason = reason;
            this.$bvModal.show("unfreeze_object_modal");
        },
        unfreezeObjectFromModal: function(evt) {
            // Prevent modal from closing
            evt.preventDefault();

            app.unfreezeInProgress = true;

            unfreezeObject(
                app.objectIdToUnfreeze,
                app.enqueueUnfrozenObject
            ).then(() => {
                app.unfreezeInProgress = false;
                this.$bvModal.hide("unfreeze_object_modal");
            });
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
        }
    }
});


var unfreezeObject = async function(objectId, enqueue) {
    var formData = new FormData();
    formData.append("object_ids", objectId);
    formData.append("enqueue", enqueue);

    var response = await apiFetch(URLMap["api.unfreeze_objects"], {
        method: "POST",
        body: formData
    });
    var data = await response.json();

    // Update search results after unfreezing the object
    return await updateResults();
};

var updateResults = async function() {
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

    var url = new URL(URLMap["api.list_frozen_objects"]);
    url.searchParams.append("search", searchQuery);
    url.searchParams.append("page", app.page);
    url.searchParams.append("limit", OBJECTS_PER_PAGE);

    var result = await apiFetch(url);
    var data = await result.json();

    app.lastPerformedSearchQuery = searchQuery;

    app.results = data["results"];
    app.resultCount = data["result_count"];
    app.pageNumbers = data["page_numbers"];
    app.page = data["page"];
    app.pageCount = data["page_count"];

    app.searchInProgress = false;
};

updateResults();
