// Run with: node tests/test_advisor.js
// Does not require a running server or install third-party dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = {window: {}};
vm.runInNewContext(fs.readFileSync('static/js/advisor.js','utf8'), context);
const a=context.window.ServiceHubAdvisor;
assert.equal(a.questions.length,3);
assert.equal(a.normalize('Cà phê ĐÁ BÓNG'),'ca phe da bong');
const data=[
  {id:1,business_id:1,name:'Bàn ăn 2 người',business_name:'Bếp Nhà Mình',category:'Nhà hàng',price:0,duration_minutes:90},
  {id:2,business_id:2,name:'Bữa tối đặc biệt',business_name:'Bếp Nhà Mình',category:'Nhà hàng',price:220000,duration_minutes:90},
  {id:3,business_id:3,name:'Cà phê sữa',business_name:'Cà phê Góc Phố',category:'Nhà hàng',price:45000,duration_minutes:40},
  {id:4,business_id:4,name:'Thuê sân pickleball',business_name:'Sân Pickleball',category:'Thể thao',price:180000,duration_minutes:60},
  {id:5,business_id:5,name:'Massage thư giãn',business_name:'An Nhiên Spa',category:'Spa',price:350000,duration_minutes:60},
  {id:6,business_id:6,name:'Cắt tóc',business_name:'Mộc Hair',category:'Làm đẹp',price:120000,duration_minutes:45}
];
function result(goal,vibe,budget){return a.recommend(data,{goal,vibe,budget});}
assert.deepEqual(Array.from(result('drink','quick','under100').map(x=>x.service.id)),[3]);
assert.deepEqual(Array.from(result('sport','active','mid').map(x=>x.service.id)),[4]);
assert.deepEqual(Array.from(result('beauty','quick','mid').map(x=>x.service.id)),[6]);
assert.deepEqual(Array.from(result('spa','calm','over300').map(x=>x.service.id)),[5]);
assert.deepEqual(Array.from(result('food','flexible','mid').map(x=>x.service.id)),[2]);
assert.equal(result('food','flexible','under100').length,0); // "Liên hệ" is not free
assert.equal(result('spa','active','under100').length,0); // never fabricate services
assert.equal(a.recommend(data,{goal:'bad',vibe:'quick',budget:'any'}).length,0);
assert.equal(result('surprise','flexible','any').length,3);
console.log('Advisor: all recommendation checks passed');
