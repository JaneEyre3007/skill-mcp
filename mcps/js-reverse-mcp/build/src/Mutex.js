/**
 * @license
 * Copyright 2025 Google Inc.
 * SPDX-License-Identifier: Apache-2.0
 */
export class Mutex {
    static Guard = class Guard {
        #mutex;
        constructor(mutex) {
            this.#mutex = mutex;
        }
        dispose() {
            return this.#mutex.release();
        }
    };
    #locked = false;
    #acquirers = [];
    // This is FIFO.
    async acquire(options = {}) {
        if (!this.#locked) {
            this.#locked = true;
            return new Mutex.Guard(this);
        }
        const { resolve, reject, promise } = Promise.withResolvers();
        let timeoutId;
        const acquire = () => {
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
            resolve();
        };
        this.#acquirers.push(acquire);
        if (options.timeoutMs !== undefined) {
            timeoutId = setTimeout(() => {
                this.#acquirers = this.#acquirers.filter(item => item !== acquire);
                reject(new Error('Timed out waiting for another tool call to finish'));
            }, options.timeoutMs);
        }
        await promise;
        return new Mutex.Guard(this);
    }
    release() {
        const resolve = this.#acquirers.shift();
        if (!resolve) {
            this.#locked = false;
            return;
        }
        resolve();
    }
}
