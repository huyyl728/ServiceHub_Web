/* Rule-based discovery assistant. All suggestions are drawn from live /api/services data.
   No external AI service, tracking, location access, or fabricated recommendations. */
(() => {
  'use strict';
  const normalize = value => String(value ?? '').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D')
    .toLowerCase().trim();

  const goals = Object.freeze([
    { id: 'food', label: 'Ăn một bữa ngon', hint: 'Quán ăn, nhà hàng, bữa sáng', icon: '🍜', keywords: ['nha hang', 'quan an', 'am thuc', 'mon an', 'bua', 'pho', 'bun', 'banh mi', 'an uong'] },
    { id: 'drink', label: 'Cà phê, đồ uống', hint: 'Ngồi trò chuyện hoặc nghỉ ngơi', icon: '☕', keywords: ['ca phe', 'cafe', 'coffee', 'tra sua', 'do uong', 'nuoc ep', 'sinh to'] },
    { id: 'sport', label: 'Chơi thể thao', hint: 'Bóng đá, pickleball, vận động', icon: '⚽', keywords: ['the thao', 'san bong', 'bong da', 'pickleball', 'tennis', 'cau long'] },
    { id: 'beauty', label: 'Làm đẹp, cắt tóc', hint: 'Salon, tóc và chăm sóc cá nhân', icon: '✂️', keywords: ['lam dep', 'cat toc', 'salon', 'hair', 'goi dau', 'tao kieu', 'barber'] },
    { id: 'spa', label: 'Spa, thư giãn', hint: 'Chăm sóc da, massage', icon: '🌿', keywords: ['spa', 'massage', 'cham soc da', 'thu gian', 'lieu trinh'] },
    { id: 'surprise', label: 'Gợi ý bất ngờ', hint: 'Khám phá dịch vụ khác nhau', icon: '✨', keywords: [] }
  ]);
  const vibes = Object.freeze([
    { id: 'quick', label: 'Nhanh gọn', hint: 'Ưu tiên dịch vụ tối đa 60 phút', icon: '⚡' },
    { id: 'calm', label: 'Nhẹ nhàng, thư giãn', hint: 'Một khoảng nghỉ cho bản thân', icon: '🌸' },
    { id: 'active', label: 'Vui vẻ, năng động', hint: 'Vận động hoặc trải nghiệm sôi nổi', icon: '🎉' },
    { id: 'flexible', label: 'Không quan trọng', hint: 'Để ServiceHub tìm lựa chọn', icon: '🧭' }
  ]);
  const budgets = Object.freeze([
    { id: 'under100', label: 'Dưới 100.000đ', hint: 'Mỗi lượt sử dụng', icon: '🍃' },
    { id: 'mid', label: '100.000–300.000đ', hint: 'Mỗi lượt sử dụng', icon: '💛' },
    { id: 'over300', label: 'Trên 300.000đ', hint: 'Mỗi lượt sử dụng', icon: '💎' },
    { id: 'any', label: 'Ngân sách linh hoạt', hint: 'Xem cả dịch vụ báo giá riêng', icon: '✨' }
  ]);
  const questions = Object.freeze([
    { title: 'Hôm nay bạn muốn ăn gì hoặc làm gì?', note: 'Chọn điều bạn đang có hứng thú.', options: goals, key: 'goal' },
    { title: 'Bạn muốn trải nghiệm theo cách nào?', note: 'Chúng mình sẽ ưu tiên dịch vụ phù hợp.', options: vibes, key: 'vibe' },
    { title: 'Bạn dự kiến chi khoảng bao nhiêu?', note: 'Chi phí được tính theo giá / lượt hiển thị trên ServiceHub.', options: budgets, key: 'budget' }
  ]);
  function textFor(service) {
    return normalize([service?.name, service?.description, service?.category, service?.business_name].filter(Boolean).join(' '));
  }
  function includesPhrase(haystack, phrase) {
    // Whole phrase match: "phở" must not match the word "phố" inside a place name.
    // Ignore punctuation but not boundaries between characters in words.
    const padded=` ${normalize(haystack).replace(/[^a-z0-9]+/g, ' ').trim()} `;
    return padded.includes(` ${normalize(phrase)} `);
  }
  function hasAny(source, terms) { return terms.some(t => includesPhrase(source, t)); }
  function goalMatch(service, goal) {
    if (goal === 'surprise') return true;
    const item = [service?.name, service?.description].filter(Boolean).join(' ');
    const category = normalize(service?.category);
    const business = service?.business_name || '';
    const food = ['nha hang','quan an','am thuc','mon an','bua','pho','bun','banh mi','com','ban an','an sang','thuc don'];
    const drinks = ['ca phe','cafe','coffee','tra sua','do uong','nuoc ep','sinh to','tra chanh'];
    if (goal === 'food') {
      if (hasAny(item, drinks) && !hasAny(item, food)) return false;
      return hasAny(category, ['nha hang','am thuc','quan an']) || hasAny(item, food);
    }
    if (goal === 'drink') {
      // Don't call a dinner offering at a coffee shop a coffee recommendation.
      if (hasAny(item, food) && !hasAny(item, drinks)) return false;
      return hasAny(item, drinks) || hasAny(category, drinks) || (hasAny(business, drinks) && !hasAny(item, food));
    }
    if (goal === 'sport') return hasAny(category, ['the thao','san bong']) || hasAny(item, ['da bong','bong da','pickleball','tennis','cau long','thue san','the thao']);
    if (goal === 'beauty') return hasAny(category, ['lam dep','salon']) || hasAny(item, ['cat toc','goi dau','nhuom toc','tao kieu','lam mong','nail','salon']);
    if (goal === 'spa') return hasAny(category, ['spa']) || hasAny(item, ['spa','massage','cham soc da','thu gian','lieu trinh']);
    return false;
  }
  function budgetMatch(service, budget) {
    if (budget === 'any') return true;
    const amount = Number(service?.price);
    // 0 means "Liên hệ" in the existing UI, not a free offering.
    if (!Number.isFinite(amount) || amount <= 0) return false;
    if (budget === 'under100') return amount < 100000;
    if (budget === 'mid') return amount >= 100000 && amount <= 300000;
    if (budget === 'over300') return amount > 300000;
    return false;
  }
  function vibePoints(service, vibe) {
    const source = textFor(service);
    const duration = Number(service?.duration_minutes);
    if (vibe === 'quick') return duration > 0 && duration <= 60 ? 10 : 0;
    if (vibe === 'calm') return ['thu gian', 'spa', 'massage', 'cham soc', 'ca phe', 'cafe', 'goi dau'].some(t => source.includes(t)) ? 10 : 0;
    if (vibe === 'active') return ['the thao', 'san bong', 'pickleball', 'tennis', 'bong da'].some(t => source.includes(t)) ? 10 : 0;
    return 0;
  }
  function explain(service, answers) {
    const reasons = [];
    const goal = goals.find(g => g.id === answers.goal);
    if (goal && goal.id !== 'surprise') reasons.push(`Liên quan đến: ${goal.label.toLowerCase()}`);
    if (answers.vibe === 'quick' && vibePoints(service, answers.vibe)) reasons.push(`Khoảng ${Number(service.duration_minutes)} phút`);
    if (answers.vibe === 'calm' && vibePoints(service, answers.vibe)) reasons.push('Phù hợp trải nghiệm thư giãn');
    if (answers.vibe === 'active' && vibePoints(service, answers.vibe)) reasons.push('Phù hợp hoạt động năng động');
    if (answers.budget !== 'any' && budgetMatch(service, answers.budget)) reasons.push('Trong khoảng ngân sách bạn chọn');
    if (!reasons.length) reasons.push('Khám phá thêm một lựa chọn có sẵn');
    return reasons.slice(0, 2);
  }
  function recommend(services, answers, limit = 3) {
    if (!answers || !goals.some(g => g.id === answers.goal) || !vibes.some(v => v.id === answers.vibe) || !budgets.some(b => b.id === answers.budget)) return [];
    const ranked = (Array.isArray(services) ? services : [])
      .filter(s => s && s.id != null && goalMatch(s, answers.goal) && budgetMatch(s, answers.budget))
      .map(s => ({ service: s, score: vibePoints(s, answers.vibe) + (Number(s.price) > 0 ? 1 : 0), reasons: explain(s, answers) }))
      .sort((a, b) => b.score - a.score || String(a.service.name || '').localeCompare(String(b.service.name || ''), 'vi'));
    // Prefer several businesses where possible, to make a recommendation useful.
    const result = [], seen = new Set();
    for (const item of ranked) {
      const key = String(item.service.business_id ?? `service-${item.service.id}`);
      if (seen.has(key)) continue;
      seen.add(key); result.push(item);
      if (result.length === limit) return result;
    }
    for (const item of ranked) {
      if (!result.includes(item)) result.push(item);
      if (result.length === limit) break;
    }
    return result;
  }
  window.ServiceHubAdvisor = Object.freeze({ questions, goals, vibes, budgets, normalize, recommend, goalMatch, budgetMatch });
})();
