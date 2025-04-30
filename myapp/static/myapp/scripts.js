document.addEventListener('DOMContentLoaded', function () {

    // Function to set up modals
    function setupModal(modalId, openButtonId, closeButtonId, cancelButtonId = null) {
        const modal = document.getElementById(modalId);
        const openButton = document.getElementById(openButtonId);
        const closeButton = document.getElementById(closeButtonId);
        const cancelButton = cancelButtonId ? document.getElementById(cancelButtonId) : null;

        if (modal && openButton && closeButton) {
            modal.style.display = "none";  // Hide modal by default

            // Open modal on button click
            openButton.onclick = () => modal.style.display = "block";

            // Close modal on close button click
            closeButton.onclick = () => modal.style.display = "none";

            // Close modal on cancel button click (if applicable)
            if (cancelButton) {
                cancelButton.onclick = () => modal.style.display = "none";
            }

            // Close modal when clicking outside of it
            window.onclick = (event) => {
                if (event.target === modal) {
                    modal.style.display = "none";
                }
            };
        }
    }

    // Initialize modals
    setupModal("modal", "openModal", "closeItemModal");
    setupModal("collectionModal", "openCollectionModal", "closeCollectionModal");

    // Patron Collection Modal with Cancel button support
    setupModal("patronCollectionModal", "openPatronCollectionModal", "closePatronCollectionModal", "cancelModal");
});
