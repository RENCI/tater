// Text selection functionality for span annotations
window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        getSelectedText: function() {
            const selection = window.getSelection();
            if (!selection || selection.toString().trim() === '') {
                return window.dash_clientside.no_update;
            }
            
            const selectedText = selection.toString();
            const range = selection.getRangeAt(0);
            
            // Get the document text element
            const docElement = document.getElementById('document-text');
            if (!docElement) {
                return window.dash_clientside.no_update;
            }
            
            // Calculate start position relative to document text
            const preRange = range.cloneRange();
            preRange.selectNodeContents(docElement);
            preRange.setEnd(range.startContainer, range.startOffset);
            const start = preRange.toString().length;
            const end = start + selectedText.length;
            
            return {
                text: selectedText,
                start: start,
                end: end
            };
        }
    }
});
