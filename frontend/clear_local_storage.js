// Script to clear local storage for the Baby Wise app
// This will be included in the frontend HTML file

function clearBabyWiseLocalStorage() {
    // Define the storage keys to clear
    const keysToRemove = [
        'SLEEP_EVENTS',
        'SLEEP_END_EVENTS',
        'FEED_EVENTS',
        'THREAD_ID',
        'LANGUAGE'
    ];
    
    // Get all keys from localStorage
    const allKeys = Object.keys(localStorage);
    
    // Filter keys that start with any of the patterns in keysToRemove
    const keysToDelete = allKeys.filter(key => 
        keysToRemove.some(pattern => key.startsWith(pattern))
    );
    
    // Count of items before deletion
    console.log(`Found ${keysToDelete.length} items to delete from localStorage`);
    
    // Delete each key
    keysToDelete.forEach(key => {
        localStorage.removeItem(key);
        console.log(`Deleted: ${key}`);
    });
    
    console.log('Local storage cleared successfully');
    
    // Show alert to user
    alert(`Cleared ${keysToDelete.length} items from local storage. The app will now reload.`);
    
    // Reload the page to apply changes
    window.location.reload();
}

// Add a button to the page to trigger the cleanup
document.addEventListener('DOMContentLoaded', function() {
    const clearButton = document.createElement('button');
    clearButton.textContent = 'Clear All Data';
    clearButton.style.position = 'fixed';
    clearButton.style.bottom = '10px';
    clearButton.style.right = '10px';
    clearButton.style.zIndex = '9999';
    clearButton.style.padding = '8px 16px';
    clearButton.style.backgroundColor = '#ff4d4d';
    clearButton.style.color = 'white';
    clearButton.style.border = 'none';
    clearButton.style.borderRadius = '4px';
    clearButton.style.cursor = 'pointer';
    
    clearButton.addEventListener('click', function() {
        if (confirm('Are you sure you want to clear all Baby Wise data? This cannot be undone.')) {
            clearBabyWiseLocalStorage();
        }
    });
    
    document.body.appendChild(clearButton);
}); 