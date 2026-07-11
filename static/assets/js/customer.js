let products = [];
let cart = new Map();
let lastCreatedOrder = null;

const $ = id => document.getElementById(id);
const money = cents =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format((cents || 0) / 100);

const esc = value => {
  const element = document.createElement('div');
  element.textContent = value ?? '';
  return element.innerHTML;
};

function setCheckoutMode(mode) {
  const button = $('finishOrder');

  if (mode === 'track') {
    button.textContent = 'Consultar pedido';
    button.dataset.mode = 'track';
    return;
  }

  button.textContent = 'Finalizar pedido';
  button.dataset.mode = 'finish';
}

async function loadProducts() {
  const response = await fetch('/api/products');
  const data = await response.json();
  products = data.items || [];

  const categories = [...new Set(products.map(product => product.category))].sort();
  $('category').innerHTML =
    '<option value="">Todas as categorias</option>' +
    categories.map(category => `<option>${esc(category)}</option>`).join('');

  renderProducts();
}

function renderProducts() {
  const query = $('search').value.toLowerCase();
  const category = $('category').value;

  $('products').innerHTML =
    products
      .filter(product =>
        (!category || product.category === category) &&
        `${product.name} ${product.description}`.toLowerCase().includes(query)
      )
      .map(product => `
        <article class="product-card">
          <span class="status">${esc(product.category)}</span>
          <h3>${esc(product.name)}</h3>
          <p>${esc(product.description)}</p>
          <div class="summary">
            <span class="price">${money(product.price_cents)}</span>
            <button class="primary" onclick="add(${product.id})">Adicionar</button>
          </div>
        </article>
      `)
      .join('') || '<p>Nenhum produto encontrado.</p>';
}

function add(id) {
  cart.set(id, (cart.get(id) || 0) + 1);
  lastCreatedOrder = null;
  setCheckoutMode('finish');
  updateCart();
}

function change(id, delta) {
  const quantity = (cart.get(id) || 0) + delta;

  if (quantity <= 0) {
    cart.delete(id);
  } else {
    cart.set(id, quantity);
  }

  if (cart.size > 0) {
    lastCreatedOrder = null;
    setCheckoutMode('finish');
  }

  updateCart();
  renderCart();
}

function total() {
  return [...cart].reduce((sum, [id, quantity]) => {
    const product = products.find(item => item.id === id);
    return sum + product.price_cents * quantity;
  }, 0);
}

function updateCart() {
  const count = [...cart.values()].reduce((sum, value) => sum + value, 0);
  $('cartCount').textContent = `${count} ${count === 1 ? 'item' : 'itens'}`;
  $('cartTotal').textContent = money(total());
}

function renderCart() {
  $('cartItems').innerHTML =
    [...cart]
      .map(([id, quantity]) => {
        const product = products.find(item => item.id === id);
        return `
          <div class="cart-row">
            <div>
              <strong>${esc(product.name)}</strong><br>
              <small>${money(product.price_cents)} cada</small>
            </div>
            <div class="qty">
              <button type="button" class="small" onclick="change(${id},-1)">−</button>
              <b>${quantity}</b>
              <button type="button" class="small" onclick="change(${id},1)">+</button>
            </div>
            <span class="price">${money(product.price_cents * quantity)}</span>
          </div>
        `;
      })
      .join('') || '<p>Carrinho vazio.</p>';

  $('cartDialogTotal').textContent = money(total());
}

function openTrackingForLastOrder() {
  if (!lastCreatedOrder) {
    return;
  }

  $('trackPhone').value = formatBrazilianPhone(lastCreatedOrder.phone);
  $('trackCode').value = lastCreatedOrder.code;

  if ($('cartDialog').open) {
    $('cartDialog').close();
  }

  if (!$('trackDialog').open) {
    $('trackDialog').showModal();
  }

  $('trackOrder').click();
}

$('search').addEventListener('input', renderProducts);
$('category').addEventListener('change', renderProducts);

$('openCart').addEventListener('click', () => {
  renderCart();
  $('customerName').value = localStorage.getItem('customer_name') || '';
  $('customerPhone').value = formatBrazilianPhone(localStorage.getItem('customer_phone') || '');

  if (cart.size > 0) {
    setCheckoutMode('finish');
  } else if (lastCreatedOrder) {
    setCheckoutMode('track');
  }

  $('cartDialog').showModal();
});

$('openTrack').addEventListener('click', () => {
  $('trackPhone').value = formatBrazilianPhone(localStorage.getItem('customer_phone') || '');

  if (lastCreatedOrder) {
    $('trackCode').value = lastCreatedOrder.code;
  }

  $('trackDialog').showModal();
});

const VALID_BRAZILIAN_DDDS = new Set([
  '11','12','13','14','15','16','17','18','19',
  '21','22','24','27','28',
  '31','32','33','34','35','37','38',
  '41','42','43','44','45','46','47','48','49',
  '51','53','54','55',
  '61','62','63','64','65','66','67','68','69',
  '71','73','74','75','77','79',
  '81','82','83','84','85','86','87','88','89',
  '91','92','93','94','95','96','97','98','99'
]);

function onlyPhoneDigits(value) {
  return String(value || '').replace(/\D/g, '').slice(0, 11);
}

function formatBrazilianPhone(value) {
  const digits = onlyPhoneDigits(value);

  if (!digits) return '';
  if (digits.length <= 2) return `(${digits}`;
  if (digits.length <= 6) return `(${digits.slice(0,2)})${digits.slice(2)}`;

  if (digits.length <= 10) {
    return `(${digits.slice(0,2)})${digits.slice(2,6)}-${digits.slice(6)}`;
  }

  return `(${digits.slice(0,2)})${digits.slice(2,7)}-${digits.slice(7)}`;
}

function applyPhoneMask(field) {
  if (!field) return;

  const cursorWasAtEnd = field.selectionStart === field.value.length;
  field.value = formatBrazilianPhone(field.value);

  if (cursorWasAtEnd) {
    const end = field.value.length;
    field.setSelectionRange(end, end);
  }
}

function isValidBrazilianPhone(value) {
  const digits = onlyPhoneDigits(value);

  if (![10, 11].includes(digits.length)) return false;
  if (!VALID_BRAZILIAN_DDDS.has(digits.slice(0, 2))) return false;
  if (/^(\d)\1+$/.test(digits.slice(2))) return false;

  return true;
}

['customerPhone', 'trackPhone'].forEach(id => {
  const field = $(id);

  field?.addEventListener('input', () => applyPhoneMask(field));
  field?.addEventListener('paste', () => {
    setTimeout(() => applyPhoneMask(field), 0);
  });
  field?.addEventListener('blur', () => applyPhoneMask(field));
});

function clearCheckoutErrors() {
  const fields = ['customerName', 'customerPhone', 'paymentMethod'];

  fields.forEach(id => {
    const field = $(id);
    const error = $(`${id}Error`);

    field?.classList.remove('invalid-field');

    if (error) {
      error.textContent = '';
    }
  });

  $('cartMessage').textContent = '';
}

function setFieldError(fieldId, message) {
  const field = $(fieldId);
  const error = $(`${fieldId}Error`);

  field?.classList.add('invalid-field');

  if (error) {
    error.textContent = message;
  }
}

function validateCheckout() {
  clearCheckoutErrors();

  const errors = [];
  const name = $('customerName').value.trim();
  const phone = $('customerPhone').value.trim();
  const normalizedPhone = onlyPhoneDigits(phone);
  const paymentMethod = $('paymentMethod').value;

  if (!name) {
    errors.push({
      field: 'customerName',
      message: 'Informe o nome completo do cliente.'
    });
  } else if (name.length < 2) {
    errors.push({
      field: 'customerName',
      message: 'O nome deve ter pelo menos 2 caracteres.'
    });
  }

  if (!phone) {
    errors.push({
      field: 'customerPhone',
      message: 'Informe o telefone com DDD.'
    });
  } else if (!isValidBrazilianPhone(phone)) {
    const ddd = normalizedPhone.slice(0, 2);
    errors.push({
      field: 'customerPhone',
      message: (
        normalizedPhone.length >= 2 && !VALID_BRAZILIAN_DDDS.has(ddd)
          ? 'Informe um DDD brasileiro válido.'
          : 'Informe um telefone válido com DDD.'
      )
    });
  }

  if (!paymentMethod) {
    errors.push({
      field: 'paymentMethod',
      message: 'Selecione a forma de pagamento.'
    });
  }

  errors.forEach(error => setFieldError(error.field, error.message));

  if (errors.length) {
    const firstField = $(errors[0].field);
    firstField?.focus();

    $('cartMessage').className = 'message';
    $('cartMessage').textContent =
      errors.length === 1
        ? errors[0].message
        : 'Preencha os campos obrigatórios destacados.';

    return false;
  }

  return true;
}

['customerName', 'customerPhone', 'paymentMethod'].forEach(id => {
  $(id)?.addEventListener('input', () => {
    $(id)?.classList.remove('invalid-field');

    const error = $(`${id}Error`);
    if (error) {
      error.textContent = '';
    }
  });

  $(id)?.addEventListener('change', () => {
    $(id)?.classList.remove('invalid-field');

    const error = $(`${id}Error`);
    if (error) {
      error.textContent = '';
    }
  });
});

$('finishOrder').addEventListener('click', async () => {
  if ($('finishOrder').dataset.mode === 'track') {
    openTrackingForLastOrder();
    return;
  }

  const message = $('cartMessage');
  message.className = 'message';
  message.textContent = '';

  if (!cart.size) {
    message.textContent = 'Adicione um produto.';
    return;
  }

  if (!validateCheckout()) {
    return;
  }

  const name = $('customerName').value.trim();
  const phone = $('customerPhone').value.trim();

  try {
    const response = await fetch('/api/orders', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        customer: {name, phone},
        paymentMethod: $('paymentMethod').value,
        notes: $('orderNotes').value,
        items: [...cart].map(([productId, quantity]) => ({
          productId,
          quantity
        }))
      })
    });

    const order = await response.json();

    if (!response.ok) {
      throw new Error(order.detail || 'Não foi possível criar o pedido.');
    }

    localStorage.setItem('customer_name', name);
    localStorage.setItem('customer_phone', phone);
    localStorage.setItem('last_order_code', order.code);

    lastCreatedOrder = {
      code: order.code,
      phone: order.customer?.phone || phone.replace(/\D/g, '')
    };

    cart.clear();
    updateCart();
    renderCart();

    $('trackPhone').value = formatBrazilianPhone(phone);
    $('trackCode').value = order.code;

    message.className = 'message success';
    message.innerHTML = `
      Pedido criado: <strong>${esc(order.code)}</strong><br>
      Total: ${money(order.totalCents)}<br>
      Clique em <strong>Consultar pedido</strong> para acompanhar.
    `;

    setCheckoutMode('track');
  } catch (error) {
    message.className = 'message';
    message.textContent = error.message;
  }
});

function trackedOrderCard(order) {
  return `
    <article class="order-card">
      <h3>${esc(order.code)}</h3>
      <span class="status ${order.status}">
        ${orderStatusLabel(order.status)}
      </span>
      <p>Cliente: <strong>${esc(order.customer.name)}</strong></p>
      <p><small>${new Date(order.createdAt).toLocaleString('pt-BR')}</small></p>
      <ul>
        ${order.items
          .map(item => `<li>${item.quantity}x ${esc(item.name)}</li>`)
          .join('')}
      </ul>
      <p class="price">${money(order.totalCents)}</p>
      <p>
        Pagamento:
        <strong>${paymentStatusLabel(order.paymentStatus)}</strong>
        · ${paymentMethodLabel(order.paymentMethod)}
      </p>
    </article>
  `;
}

async function queryTrackedOrders() {
  const output = $('trackResult');
  const phone = $('trackPhone').value.trim();
  const code = $('trackCode').value.trim();

  if (!phone && !code) {
    output.innerHTML =
      '<p class="message">Informe o telefone ou o código do pedido.</p>';
    return;
  }

  output.innerHTML = '<p>Consultando...</p>';

  try {
    const params = new URLSearchParams();

    if (phone) {
      params.set('phone', phone);
    }

    if (code) {
      params.set('code', code);
    }

    const response = await fetch(`/api/orders/track?${params.toString()}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Pedido não encontrado.');
    }

    const items = data.items || [];

    output.innerHTML = items.length
      ? `
        <p class="track-count">
          ${items.length}
          ${items.length === 1 ? 'pedido encontrado' : 'pedidos encontrados'}.
        </p>
        <div class="tracked-orders">
          ${items.map(trackedOrderCard).join('')}
        </div>
      `
      : '<p class="message">Pedido não encontrado.</p>';
  } catch (error) {
    output.innerHTML = `<p class="message">${esc(error.message)}</p>`;
  }
}

$('trackOrder').addEventListener('click', queryTrackedOrders);

loadProducts();

connectRealtime((event, payload) => {
  const savedPhone =
    (localStorage.getItem('customer_phone') || '').replace(/\D/g, '');

  const trackedCode = $('trackCode')?.value.trim();
  const trackedPhone = $('trackPhone')?.value.replace(/\D/g, '');
  const trackedDialogIsOpen = Boolean($('trackDialog')?.open);

  const belongsToCustomer =
    payload?.customer?.phone === savedPhone ||
    payload?.customer?.phone === trackedPhone;

  const matchesOpenQuery =
    trackedCode === payload?.code ||
    (trackedPhone && trackedPhone === payload?.customer?.phone);

  if (event === 'ORDER_STATUS_CHANGED' && belongsToCustomer) {
    notify(
      'Atualização do pedido',
      `${payload.code}: ${orderStatusLabel(payload.status)}`,
      'success'
    );

    if (trackedDialogIsOpen && matchesOpenQuery) {
      queryTrackedOrders();
    }
  }

  if (event === 'PAYMENT_CONFIRMED' && belongsToCustomer) {
    notify(
      'Pagamento confirmado',
      `Pedido ${payload.code}`,
      'success'
    );

    if (trackedDialogIsOpen && matchesOpenQuery) {
      queryTrackedOrders();
    }
  }
});
