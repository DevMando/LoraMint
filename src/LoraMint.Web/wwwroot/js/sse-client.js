/**
 * SSE Client for LoraMint image generation and training progress streaming
 */
window.SseClient = {
    abortController: null,
    trainingAbortController: null,

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
    },

    /**
     * Start LoRA training with SSE progress streaming
     * @param {string} url - The SSE endpoint URL
     * @param {FormData} formData - The FormData with training params and files
     * @param {object} dotNetHelper - DotNet object reference for callbacks
     */
    startTraining: function (url, formData, dotNetHelper) {
        // Cancel any existing training request
        this.stopTraining();

        // Create new abort controller
        this.trainingAbortController = new AbortController();

        // Start fetch with streaming (FormData for file uploads)
        fetch(url, {
            method: 'POST',
            headers: {
                'Accept': 'text/event-stream'
                // Note: Don't set Content-Type for FormData - browser will set it with boundary
            },
            body: formData,
            signal: this.trainingAbortController.signal
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
                    console.log('Training SSE request was cancelled');
                } else {
                    console.error('Training SSE error:', error);
                    dotNetHelper.invokeMethodAsync('OnError', error.message);
                }
            });
    },

    /**
     * Stop/cancel the current training
     */
    stopTraining: function () {
        if (this.trainingAbortController) {
            this.trainingAbortController.abort();
            this.trainingAbortController = null;
        }
    }
};

/**
 * Training Client for LoRA training with file uploads and SSE progress streaming
 */
window.TrainingClient = {
    abortController: null,

    /**
     * Start LoRA training with SSE progress streaming
     * @param {string} url - The SSE endpoint URL
     * @param {string} loraName - Name for the LoRA
     * @param {string} userId - User identifier
     * @param {Array} files - Array of {name, content (base64), contentType}
     * @param {object} settings - Training settings {fast_mode, num_train_epochs, learning_rate, lora_rank, with_prior_preservation}
     * @param {object} dotNetHelper - DotNet object reference for callbacks
     */
    startTraining: function (url, loraName, userId, files, settings, dotNetHelper) {
        // Cancel any existing request
        this.stopTraining();

        // Create new abort controller
        this.abortController = new AbortController();

        // Build FormData
        const formData = new FormData();
        formData.append('lora_name', loraName);
        formData.append('user_id', userId);

        // Add training settings
        if (settings) {
            if (settings.fast_mode !== undefined) {
                formData.append('fast_mode', settings.fast_mode.toString());
            }
            if (settings.num_train_epochs !== null && settings.num_train_epochs !== undefined) {
                formData.append('num_train_epochs', settings.num_train_epochs.toString());
            }
            if (settings.learning_rate !== undefined) {
                formData.append('learning_rate', settings.learning_rate.toString());
            }
            if (settings.lora_rank !== undefined) {
                formData.append('lora_rank', settings.lora_rank.toString());
            }
            if (settings.with_prior_preservation !== undefined) {
                formData.append('with_prior_preservation', settings.with_prior_preservation.toString());
            }
        }

        // Convert base64 files back to Blobs and add to FormData
        for (const file of files) {
            const binaryStr = atob(file.content);
            const bytes = new Uint8Array(binaryStr.length);
            for (let i = 0; i < binaryStr.length; i++) {
                bytes[i] = binaryStr.charCodeAt(i);
            }
            const blob = new Blob([bytes], { type: file.contentType });
            formData.append('images', blob, file.name);
        }

        // Start fetch with streaming
        fetch(url, {
            method: 'POST',
            headers: {
                'Accept': 'text/event-stream'
            },
            body: formData,
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
                            if (buffer.trim()) {
                                this.processLines(buffer, dotNetHelper);
                            }
                            break;
                        }

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || '';

                        for (const line of lines) {
                            this.processLine(line, dotNetHelper);
                        }
                    }
                };

                return processStream();
            })
            .catch(error => {
                if (error.name === 'AbortError') {
                    console.log('Training request was cancelled');
                } else {
                    console.error('Training SSE error:', error);
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
                console.error('Failed to parse training SSE data:', e, jsonStr);
            }
        }
    },

    /**
     * Process multiple lines
     */
    processLines: function (text, dotNetHelper) {
        const lines = text.split('\n');
        for (const line of lines) {
            this.processLine(line, dotNetHelper);
        }
    },

    /**
     * Stop/cancel the current training
     */
    stopTraining: function () {
        if (this.abortController) {
            this.abortController.abort();
            this.abortController = null;
        }
    }
};
