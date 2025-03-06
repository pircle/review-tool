// JavaScript test file for multi-language support

// Simple function
function greet(name) {
    console.log(`Hello, ${name}!`);
    return `Hello, ${name}!`;
}

// Complex function with nested conditionals
function processData(data, options) {
    if (!data) {
        return null;
    }
    
    let result = [];
    
    if (options && options.filter) {
        if (options.filter.type === 'include') {
            if (options.filter.values && options.filter.values.length > 0) {
                result = data.filter(item => options.filter.values.includes(item.id));
            } else {
                result = data;
            }
        } else if (options.filter.type === 'exclude') {
            if (options.filter.values && options.filter.values.length > 0) {
                result = data.filter(item => !options.filter.values.includes(item.id));
            } else {
                result = data;
            }
        } else {
            result = data;
        }
    } else {
        result = data;
    }
    
    if (options && options.sort) {
        if (options.sort.field) {
            result.sort((a, b) => {
                if (a[options.sort.field] < b[options.sort.field]) return -1;
                if (a[options.sort.field] > b[options.sort.field]) return 1;
                return 0;
            });
            
            if (options.sort.direction === 'desc') {
                result.reverse();
            }
        }
    }
    
    return result;
}

// Arrow function
const multiply = (a, b) => a * b;

// Class definition
class Person {
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }
    
    greet() {
        return `Hello, my name is ${this.name} and I am ${this.age} years old.`;
    }
    
    static create(name, age) {
        return new Person(name, age);
    }
}

// Export
module.exports = {
    greet,
    processData,
    multiply,
    Person
}; 