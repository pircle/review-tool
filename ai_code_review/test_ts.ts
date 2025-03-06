// TypeScript test file for multi-language support

// Type definitions
interface User {
    id: number;
    name: string;
    email: string;
    age?: number;
}

type SortDirection = 'asc' | 'desc';

interface SortOptions {
    field: string;
    direction: SortDirection;
}

interface FilterOptions {
    type: 'include' | 'exclude';
    values: number[];
}

interface ProcessOptions {
    filter?: FilterOptions;
    sort?: SortOptions;
}

// Simple function with type annotations
function greet(name: string): string {
    console.log(`Hello, ${name}!`);
    return `Hello, ${name}!`;
}

// Complex function with nested conditionals and type annotations
function processData(data: User[], options?: ProcessOptions): User[] | null {
    if (!data) {
        return null;
    }
    
    let result: User[] = [];
    
    if (options && options.filter) {
        if (options.filter.type === 'include') {
            if (options.filter.values && options.filter.values.length > 0) {
                result = data.filter(item => options.filter!.values.includes(item.id));
            } else {
                result = data;
            }
        } else if (options.filter.type === 'exclude') {
            if (options.filter.values && options.filter.values.length > 0) {
                result = data.filter(item => !options.filter!.values.includes(item.id));
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
                if (a[options.sort!.field] < b[options.sort!.field]) return -1;
                if (a[options.sort!.field] > b[options.sort!.field]) return 1;
                return 0;
            });
            
            if (options.sort.direction === 'desc') {
                result.reverse();
            }
        }
    }
    
    return result;
}

// Arrow function with type annotations
const multiply = (a: number, b: number): number => a * b;

// Class definition with type annotations
class Person {
    name: string;
    age: number;
    
    constructor(name: string, age: number) {
        this.name = name;
        this.age = age;
    }
    
    greet(): string {
        return `Hello, my name is ${this.name} and I am ${this.age} years old.`;
    }
    
    static create(name: string, age: number): Person {
        return new Person(name, age);
    }
}

// Generic class
class DataStore<T> {
    private items: T[] = [];
    
    add(item: T): void {
        this.items.push(item);
    }
    
    getAll(): T[] {
        return this.items;
    }
}

// Export
export {
    User,
    SortDirection,
    SortOptions,
    FilterOptions,
    ProcessOptions,
    greet,
    processData,
    multiply,
    Person,
    DataStore
}; 