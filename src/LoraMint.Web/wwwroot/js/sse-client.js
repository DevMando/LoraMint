/**
 * SSE Client for LoraMint image generation progress streaming
 */
window.SseClient = {
    abortController: null,

    /**
     * Start image generation with SSE progress streaming
     * @param {string} url - The SSE endpoint URL
     * @param {object} requestBody - The request body to send
     * @param {object} dotNetHelper - DotNet object reference for callbacks
     */
    startGeneration: function (url, requestBody, dotNetHelper) {
        // Cancel any existing request
        this.stopGeneration();

        // Create new abort controller
        this.abortController = new AbortController();

        // Start fetch with streaming
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            body: JSON.stringify(requestBody),
            signal: this.abortController.signal
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                const processStream = async () => {
                    while (true) {
                        const { done, value } = await reader.read();

                        if (done) {
                            // Process any remaining data in buffer
                            if (buffer.trim()) {
                                this.processLines(buffer, dotNetHelper);
                            }
                            break;
                        }

                        // Decode and add to buffer
                        buffer += decoder.decode(value, { stream: true });

                        // Process complete lines
                        const lines = buffer.split('\n');
                        // Keep the last incomplete line in buffer
                        buffer = lines.pop() || '';

                        // Process complete lines
                        for (const line of lines) {
                            this.processLine(line, dotNetHelper);
                        }
                    }
                };

                return processStream();
            })
            .catch(error => {
                if (error.name === 'AbortError') {
                    console.log('SSE request was cancelled');
                } else {
                    console.error('SSE error:', error);
                    dotNetHelper.invokeMethodAsync('OnError', error.message);
                }
            });
    },

    /**
     * Process a single SSE line
     */
    processLine: function (line, dotNetHelper) {
        const trimmedLine = line.trim();
        if (trimmedLine.startsWith('data: ')) {
            const jsonStr = trimmedLine.substring(6);
            try {
                const data = JSON.parse(jsonStr);
                dotNetHelper.invokeMethodAsync('OnProgressEvent', data);
            } catch (e) {
                console.error('Failed to parse SSE data:', e, jsonStr);
            }
        }
    },

    /**
     * Process multiple lines (for remaining buffer)
     */
    processLines: function (text, dotNetHelper) {
        const lines = text.split('\n');
        for (const line of lines) {
            this.processLine(line, dotNetHelper);
        }
    },

    /**
     * Stop/cancel the current generation
     */
    stopGeneration: function () {
        if (this.abortController) {
            this.abortController.abort();
            this.abortController = null;
        }
    }
};
