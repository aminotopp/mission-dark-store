import json
import os
import psycopg2
from typing import Dict, Any

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    '''
    Business: Handle admin operations - verify password, update status, delete orders and messages
    Args: event - dict with httpMethod, body (action: verify/update_status/delete, password, type, id, status)
          context - object with attributes: request_id, function_name
    Returns: HTTP response dict
    '''
    method: str = event.get('httpMethod', 'GET')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '86400'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Method not allowed'}),
            'isBase64Encoded': False
        }
    
    body_data = json.loads(event.get('body', '{}'))
    action = body_data.get('action')
    
    if not action:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Missing action'}),
            'isBase64Encoded': False
        }
    
    # Handle verify action
    if action == 'verify':
        password = body_data.get('password')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        
        if not admin_password:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Admin password not configured'}),
                'isBase64Encoded': False
            }
        
        is_valid = password == admin_password
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'valid': is_valid,
                'message': 'Password verified' if is_valid else 'Invalid password'
            }),
            'isBase64Encoded': False
        }
    
    # Handle delete, update_status, update_product and add_product actions
    item_type = body_data.get('type')
    item_id = body_data.get('id')
    
    if action == 'add_product':
        database_url = os.environ.get('DATABASE_URL')
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        name = body_data.get('name')
        price = body_data.get('price')
        description = body_data.get('description', '')
        sizes = body_data.get('sizes', ['S', 'M', 'L', 'XL'])
        image = body_data.get('image')
        in_stock = body_data.get('inStock', True)
        category = body_data.get('category', 'Основное')
        
        if not all([name, price, image]):
            conn.close()
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Missing required fields: name, price, image'}),
                'isBase64Encoded': False
            }
        
        cursor.execute('''
            INSERT INTO t_p54427834_mission_dark_store.products (id, name, price, description, sizes, image, in_stock, category)
            VALUES (gen_random_uuid()::text, %s, %s, %s, %s, %s, %s, %s)
        ''', (name, price, description, sizes, image, in_stock, category))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'success': True, 'message': 'Product added'}),
            'isBase64Encoded': False
        }
    
    if action == 'update_product':
        database_url = os.environ.get('DATABASE_URL')
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        update_fields = []
        params = []
        
        if 'name' in body_data:
            update_fields.append('name = %s')
            params.append(body_data['name'])
        
        if 'price' in body_data:
            update_fields.append('price = %s')
            params.append(body_data['price'])
        
        if 'description' in body_data:
            update_fields.append('description = %s')
            params.append(body_data['description'])
        
        if 'inStock' in body_data:
            update_fields.append('in_stock = %s')
            params.append(body_data['inStock'])
        
        if 'sizes' in body_data:
            update_fields.append('sizes = %s')
            params.append(body_data['sizes'])
        
        if 'image' in body_data:
            update_fields.append('image = %s')
            params.append(body_data['image'])
        
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        params.append(item_id)
        
        query = f'''
            UPDATE t_p54427834_mission_dark_store.products
            SET {', '.join(update_fields)}
            WHERE id = %s
        '''
        
        cursor.execute(query, params)
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'success': True, 'message': 'Product updated'}),
            'isBase64Encoded': False
        }
    
    if not all([item_type, item_id]):
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Missing required fields'}),
            'isBase64Encoded': False
        }
    
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    if action == 'delete':
        if item_type == 'order':
            cursor.execute("DELETE FROM t_p54427834_mission_dark_store.orders WHERE id = %s", (item_id,))
        elif item_type == 'message':
            cursor.execute("DELETE FROM t_p54427834_mission_dark_store.contact_messages WHERE id = %s", (item_id,))
        elif item_type == 'product':
            cursor.execute("DELETE FROM t_p54427834_mission_dark_store.products WHERE id = %s", (item_id,))
        else:
            conn.close()
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Invalid type'}),
                'isBase64Encoded': False
            }
    elif action == 'update_status':
        status = body_data.get('status')
        if not status:
            conn.close()
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Missing status'}),
                'isBase64Encoded': False
            }
        cursor.execute("UPDATE t_p54427834_mission_dark_store.orders SET status = %s WHERE id = %s", (status, item_id))
    else:
        conn.close()
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Invalid action'}),
            'isBase64Encoded': False
        }
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'success': True,
            'message': 'Action completed successfully'
        }),
        'isBase64Encoded': False
    }