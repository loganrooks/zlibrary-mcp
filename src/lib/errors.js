"use strict";
/**
 * Custom error classes for Z-Library MCP
 * Implements the pattern from .claude/PATTERNS.md
 */
var __extends = (this && this.__extends) || (function () {
    var extendStatics = function (d, b) {
        extendStatics = Object.setPrototypeOf ||
            ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
            function (d, b) { for (var p in b) if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p]; };
        return extendStatics(d, b);
    };
    return function (d, b) {
        if (typeof b !== "function" && b !== null)
            throw new TypeError("Class extends value " + String(b) + " is not a constructor or null");
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    };
})();
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.TimeoutError = exports.PythonBridgeError = exports.DomainError = exports.AuthenticationError = exports.NetworkError = exports.ZLibraryError = void 0;
/**
 * Custom error class for Z-Library operations with context enrichment
 */
var ZLibraryError = /** @class */ (function (_super) {
    __extends(ZLibraryError, _super);
    function ZLibraryError(message, code, context, retryable, fatal) {
        if (retryable === void 0) { retryable = true; }
        if (fatal === void 0) { fatal = false; }
        var _this = _super.call(this, message) || this;
        _this.code = code;
        _this.context = context;
        _this.retryable = retryable;
        _this.fatal = fatal;
        _this.name = 'ZLibraryError';
        // Maintain proper stack trace in V8 environments
        if (Error.captureStackTrace) {
            Error.captureStackTrace(_this, ZLibraryError);
        }
        return _this;
    }
    /**
     * Create a ZLibraryError from any error object with context enrichment
     * @param error - The original error
     * @param context - Additional context to attach
     * @returns Enriched ZLibraryError instance
     */
    ZLibraryError.fromError = function (error, context) {
        if (error instanceof ZLibraryError) {
            return error;
        }
        var message = error.message || String(error);
        var code = error.code || 'UNKNOWN_ERROR';
        // Determine if error is retryable based on code
        var retryable = !['AUTH_ERROR', 'FORBIDDEN', 'INVALID_INPUT', 'VALIDATION_ERROR'].includes(code);
        return new ZLibraryError(message, code, __assign(__assign({}, context), { originalError: error, stack: error.stack, timestamp: new Date().toISOString() }), retryable);
    };
    /**
     * Convert error to a JSON-serializable object
     */
    ZLibraryError.prototype.toJSON = function () {
        return {
            name: this.name,
            message: this.message,
            code: this.code,
            context: this.context,
            retryable: this.retryable,
            fatal: this.fatal,
            stack: this.stack
        };
    };
    return ZLibraryError;
}(Error));
exports.ZLibraryError = ZLibraryError;
/**
 * Error thrown when network operations fail
 */
var NetworkError = /** @class */ (function (_super) {
    __extends(NetworkError, _super);
    function NetworkError(message, context) {
        var _this = _super.call(this, message, 'NETWORK_ERROR', context, true, false) || this;
        _this.name = 'NetworkError';
        return _this;
    }
    return NetworkError;
}(ZLibraryError));
exports.NetworkError = NetworkError;
/**
 * Error thrown when authentication fails
 */
var AuthenticationError = /** @class */ (function (_super) {
    __extends(AuthenticationError, _super);
    function AuthenticationError(message, context) {
        var _this = _super.call(this, message, 'AUTH_ERROR', context, false, true) || this;
        _this.name = 'AuthenticationError';
        return _this;
    }
    return AuthenticationError;
}(ZLibraryError));
exports.AuthenticationError = AuthenticationError;
/**
 * Error thrown when a domain is unavailable
 */
var DomainError = /** @class */ (function (_super) {
    __extends(DomainError, _super);
    function DomainError(message, context) {
        var _this = _super.call(this, message, 'DOMAIN_ERROR', context, true, false) || this;
        _this.name = 'DomainError';
        return _this;
    }
    return DomainError;
}(ZLibraryError));
exports.DomainError = DomainError;
/**
 * Error thrown when the Python bridge fails
 */
var PythonBridgeError = /** @class */ (function (_super) {
    __extends(PythonBridgeError, _super);
    function PythonBridgeError(message, context, retryable) {
        if (retryable === void 0) { retryable = true; }
        var _this = _super.call(this, message, 'PYTHON_ERROR', context, retryable, false) || this;
        _this.name = 'PythonBridgeError';
        return _this;
    }
    return PythonBridgeError;
}(ZLibraryError));
exports.PythonBridgeError = PythonBridgeError;
/**
 * Error thrown when operation times out
 */
var TimeoutError = /** @class */ (function (_super) {
    __extends(TimeoutError, _super);
    function TimeoutError(message, context) {
        var _this = _super.call(this, message, 'TIMEOUT', context, true, false) || this;
        _this.name = 'TimeoutError';
        return _this;
    }
    return TimeoutError;
}(ZLibraryError));
exports.TimeoutError = TimeoutError;
