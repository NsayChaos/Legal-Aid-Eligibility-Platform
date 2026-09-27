const test=require('node:test');
const assert=require('node:assert/strict');
const {calculateImpact}=require('../impact.js');
test('estimates annual released hours and capacity without claiming cash savings',()=>{const r=calculateImpact({intakes:400,minutes:12,cost:45,hoursPerMatter:8});assert.equal(r.hours,960);assert.equal(r.capacity,120);assert.equal(r.value,43200);});
test('zero time saving produces zero benefit',()=>assert.equal(calculateImpact({intakes:400,minutes:0,cost:45,hoursPerMatter:8}).capacity,0));
test('rejects invalid or unsafe scenario assumptions',()=>{for(const v of [-1,NaN,Infinity,'100'])assert.throws(()=>calculateImpact({intakes:v,minutes:12,cost:45,hoursPerMatter:8}));assert.throws(()=>calculateImpact({intakes:10,minutes:10,cost:40,hoursPerMatter:0}));});
