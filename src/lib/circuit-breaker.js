"use strict";
/**
 * Circuit Breaker pattern implementation for Z-Library MCP
 * Implements the pattern from .claude/PATTERNS.md
 * Prevents cascading failures by opening circuit after repeated failures
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
exports.CircuitBreaker = void 0;
var CircuitBreaker = /** @class */ (function () {
    function CircuitBreaker(options) {
        if (options === void 0) { options = {}; }
        var _a, _b;
        this.failureCount = 0;
        this.lastFailureTime = null;
        this.state = 'CLOSED';
        this.threshold = (_a = options.threshold) !== null && _a !== void 0 ? _a : 5;
        this.timeout = (_b = options.timeout) !== null && _b !== void 0 ? _b : 60000;
        this.onStateChange = options.onStateChange;
    }
    /**
     * Execute an operation through the circuit breaker
     * @param operation - The async operation to execute
     * @returns Promise resolving with the operation result
     * @throws Error if circuit is OPEN or operation fails
     */
    CircuitBreaker.prototype.execute = function (operation) {
        return __awaiter(this, void 0, void 0, function () {
            var result, error_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.state === 'OPEN') {
                            if (this.lastFailureTime && Date.now() - this.lastFailureTime > this.timeout) {
                                this.transitionTo('HALF_OPEN');
                            }
                            else {
                                throw new Error('Circuit breaker is OPEN');
                            }
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, operation()];
                    case 2:
                        result = _a.sent();
                        this.onSuccess();
                        return [2 /*return*/, result];
                    case 3:
                        error_1 = _a.sent();
                        this.onFailure();
                        throw error_1;
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    /**
     * Get current circuit breaker state
     */
    CircuitBreaker.prototype.getState = function () {
        return this.state;
    };
    /**
     * Get current failure count
     */
    CircuitBreaker.prototype.getFailureCount = function () {
        return this.failureCount;
    };
    /**
     * Manually reset the circuit breaker to CLOSED state
     */
    CircuitBreaker.prototype.reset = function () {
        this.failureCount = 0;
        this.lastFailureTime = null;
        this.transitionTo('CLOSED');
    };
    CircuitBreaker.prototype.onSuccess = function () {
        this.failureCount = 0;
        this.transitionTo('CLOSED');
    };
    CircuitBreaker.prototype.onFailure = function () {
        this.failureCount++;
        this.lastFailureTime = Date.now();
        if (this.failureCount >= this.threshold) {
            this.transitionTo('OPEN');
            console.error('Circuit breaker opened due to repeated failures', {
                failureCount: this.failureCount,
                threshold: this.threshold,
                lastFailureTime: new Date(this.lastFailureTime).toISOString()
            });
        }
    };
    CircuitBreaker.prototype.transitionTo = function (newState) {
        if (this.state !== newState) {
            var oldState = this.state;
            this.state = newState;
            console.log("Circuit breaker state transition: ".concat(oldState, " -> ").concat(newState));
            if (this.onStateChange) {
                this.onStateChange(oldState, newState);
            }
        }
    };
    return CircuitBreaker;
}());
exports.CircuitBreaker = CircuitBreaker;
