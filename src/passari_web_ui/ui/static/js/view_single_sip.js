var app = new Vue({
    el: "#sip_reports_app",
    data: {
        // 'sipFilename' and 'logFilenames' are provided in the Flask template
        sipFilename: sipFilename,
        logFilenames: logFilenames,
        logContents: {},
        logBlobURLs: {}
    },
    methods: {
        loadLogFileForTab: function(tabIndex) {
            app.loadLogFile(app.logFilenames[tabIndex]);
        },
        loadLogFile: function(filename) {
            loadLogFile(filename);
        }
    }
});

var loadLogFile = async function(filename) {
    if (filename in app.logContents) {
        // Don't load a log file we have already loaded or are loading
        return;
    }

    // Set the content to null first; this means the download is underway
    Vue.set(app.logContents, filename, null)

    var url = new URL(URLMap["api.get_log_content"]);
    url.searchParams.append("sip_filename", app.sipFilename);
    url.searchParams.append("log_filename", filename);

    var result = await apiFetch(url);
    var data = await result.json();

    Vue.set(app.logContents, filename, data["data"]);

    if (filename.endsWith(".html")) {
        // Create a Blob URL for HTML documents so they can be embedded
        // more safely without having to loosen the CSP rules too much
        Vue.set(
            app.logBlobURLs, filename,
            URL.createObjectURL(new Blob([data["data"]]))
        );
    }
};
