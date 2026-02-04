"use strict";
/**
 * Retry logic with exponential backoff for Z-Library MCP
 * Implements the pattern from .claude/PATTERNS.md
 */
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.withRetry = withRetry;
exports.isRetryableError = isRetryableError;
/**
 * Execute an operation with retry logic and exponential backoff
 * @param operation - The async operation to execute
 * @param options - Retry configuration options
 * @returns Promise resolving with the operation result
 * @throws The last error if all retries are exhausted
 */
function withRetry(operation_1) {
    return __awaiter(this, arguments, void 0, function (operation, options) {
        var _a, maxRetries, _b, initialDelay, _c, maxDelay, _d, factor, _e, shouldRetry, onRetry, lastError, delay, attempt, error_1, errorMessage;
        if (options === void 0) { options = {}; }
        return __generator(this, function (_f) {
            switch (_f.label) {
                case 0:
                    _a = options.maxRetries, maxRetries = _a === void 0 ? 3 : _a, _b = options.initialDelay, initialDelay = _b === void 0 ? 1000 : _b, _c = options.maxDelay, maxDelay = _c === void 0 ? 30000 : _c, _d = options.factor, factor = _d === void 0 ? 2 : _d, _e = options.shouldRetry, shouldRetry = _e === void 0 ? function (error) { return !error.fatal; } : _e, onRetry = options.onRetry;
                    delay = initialDelay;
                    attempt = 0;
                    _f.label = 1;
                case 1:
                    if (!(attempt <= maxRetries)) return [3 /*break*/, 7];
                    _f.label = 2;
                case 2:
                    _f.trys.push([2, 4, , 6]);
                    return [4 /*yield*/, operation()];
                case 3: return [2 /*return*/, _f.sent()];
                case 4:
                    error_1 = _f.sent();
                    lastError = error_1;
                    if (attempt === maxRetries || !shouldRetry(error_1)) {
                        throw error_1;
                    }
                    errorMessage = error_1 instanceof Error ? error_1.message : String(error_1);
                    console.log("Attempt ".concat(attempt + 1, " failed, retrying in ").concat(delay, "ms..."), {
                        error: errorMessage,
                        attempt: attempt + 1,
                        maxRetries: maxRetries,
                        delay: delay
                    });
                    // Call custom retry callback if provided
                    if (onRetry) {
                        onRetry(attempt + 1, error_1, delay);
                    }
                    // Wait before retry
                    return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, delay); })];
                case 5:
                    // Wait before retry
                    _f.sent();
                    // Calculate next delay with exponential backoff
                    delay = Math.min(delay * factor, maxDelay);
                    return [3 /*break*/, 6];
                case 6:
                    attempt++;
                    return [3 /*break*/, 1];
                case 7: throw lastError;
            }
        });
    });
}
/**
 * Determine if an error is retryable based on error characteristics
 * @param error - The error to classify
 * @returns true if the error should trigger a retry
 */
function isRetryableError(error) {
    var _a, _b;
    // Fatal errors that should not be retried
    if (error.fatal === true) {
        return false;
    }
    // Authentication/authorization errors are not retryable
    if (error.code === 'AUTH_ERROR' || error.code === 'FORBIDDEN') {
        return false;
    }
    // Invalid input errors are not retryable
    if (error.code === 'INVALID_INPUT' || error.code === 'VALIDATION_ERROR') {
        return false;
    }
    // Network errors are retryable
    if (error.code === 'NETWORK_ERROR' ||
        error.code === 'TIMEOUT' ||
        error.code === 'ECONNREFUSED' ||
        error.code === 'ENOTFOUND' ||
        error.code === 'ETIMEDOUT') {
        return true;
    }
    // Python bridge errors might be transient
    if (error.code === 'PYTHON_ERROR') {
        // Check if it's a transient Python error
        var message = ((_a = error.message) === null || _a === void 0 ? void 0 : _a.toLowerCase()) || '';
        if (message.includes('timeout') ||
            message.includes('connection') ||
            message.includes('network')) {
            return true;
        }
    }
    // Domain/server errors are retryable
    if (error.code === 'DOMAIN_ERROR' ||
        error.code === 'SERVER_ERROR' ||
        ((_b = error.code) === null || _b === void 0 ? void 0 : _b.startsWith('5'))) {
        return true;
    }
    // Default to not retryable if we can't classify
    return false;
}
