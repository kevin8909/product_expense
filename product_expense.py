# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Autor:Kevin Kong (kfx2007@163.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api,models,_,fields
from openerp import workflow
<<<<<<< HEAD
from openerp.exceptions import except_orm,Warning
from datetime import datetime
from openerp.osv import osv

class hr_department(models.Model):
    _inherit="hr.department"

    @api.model 
    def name_search(self,name='',args=None,operator='ilike',limit=100):
        departs = self.search([('name',operator,name)])    
        departs = self._search_department(departs)    
        if len(departs):
            return departs.name_get()
        return super(hr_department,self).name_search(name=name,args=args,operator=operator,limit=limit)

    @api.model
    def _search_department(self,departs):
        for depart in departs:
            sub_departs = self.search([('parent_id','=',depart.id)])
            departs += self._search_department(sub_departs)
        return departs

class product_expense(models.Model):
    _name='product.expense'

    _inherit = ['mail.thread', 'ir.needaction_mixin']  

    @api.cr_uid_context
    def _get_default_user(self,cr,uid,context):
        users = self.pool.get('hr.employee').search(cr,uid,[('user_id','=',uid)],context=context)
        if not len(users):
            raise except_orm(_('Error'),_('No staff map your current user!'))
        return users[0]
    
    name = fields.Char('Name',readonly=True)
    staff = fields.Many2one('hr.employee','Employee',required=True)
    department = fields.Many2one('hr.department',string='Department',related="staff.department_id")
    date = fields.Date('Date')
    expense_line = fields.One2many('product.expense.line','expense_id','Products',states={'draft':[('readonly',False)],'confirm':[('readonly',True)],'accepted':

[('readonly',True)],'waiting':[('readonly',True)],'done':[('readonly',True)],'refused':[('readonly',True)]})
    state = fields.Selection(selection=[('draft','Draft'),('confirm','Confirm'),('accepted','Accepted'),('waiting','Waiting'),('receive','Receive'),('done','Done'),

('refused','Refused')],string="Status")
    amount = fields.Float('Amount',compute="_get_amount")
    note = fields.Text('Free Notes')
    ref_no = fields.Many2one('stock.picking','Ref Delivery',readonly=True)

    _defaults={
        'staff':_get_default_user,
    }   

    _order = "date desc"

    @api.one
    def _get_amount(self):
        for line in self.expense_line:
            self.amount += line.subtotal
    
    def action_confirm(self):
        self.state='confirm'
        self.message_post(body=_('Confirmed the order'))

    def action_accept(self):
        self.state='accepted'
        self.message_post(body=_('Accepted the order'))

    def action_refuse(self):
        self.state='refused'
        self.message_post(body=_('Refused the order'))

    def do_transfer(self):
            if self.on_ship_create():
                self.state='waiting'
                self.message_post(body=_('created the deliver order'))

    @api.one
    def on_ship_create(self):
        """
        Create the delivery order according to product expense order.
        """
        picking_obj = self.env['stock.picking']
        picking_type_obj = self.env['stock.picking.type']
        picking_type = picking_type_obj.search([('default_location_src_id','=',self.staff.department_id.expense_location.id),('code','=','outgoing')])
        if not picking_type:
                raise except_orm(_('Warning!'),_("there's no proper location for your department. Please set your department properly!"))

        if not self.ref_no:
            picking_id = picking_obj.create({
                    "partner_id":self.staff.address_home_id.id,
                    "picking_type_id":picking_type[0].id,
                    "origin":self.name,
                    })

            self.ref_no = picking_id 

        stock_move_obj = self.env['stock.move']
        stock_quant_obj = self.env['stock.quant']
        expense_loc = self.env['stock.location'].search([('name','=','Expense')])
        if not expense_loc:
            raise except_orm(_('Warning!'),_("You haven't set expense location"))
        for line in self.expense_line:
            #get the out location's quants
            quants = self.env['stock.quant'].search([('location_id','=',self.staff.department_id.expense_location.id),('product_id','=',line.product.id)])
            qty = sum([q.qty for q in quants])
            if qty < line.quantity:
                raise except_orm(_('Warning!'),_('Product '+line.product.name+' has not enough quantity.'))

            stock_move_obj.create({
                'picking_id':picking_id.id,
                'product_id':line.product.id,
                'procure_method':'make_to_stock',
                'product_uom_qty':line.quantity,
                'product_uom':line.price_unit.id,
                'name':self.name,
                'location_id':self.staff.department_id.expense_location.id,
                'location_dest_id':expense_loc.id,
                'price_unit':line.product.standard_price,
                })
        #do transfter
        self.ref_no.action_confirm()
        return True

    @api.one
    @api.constrains('expense_line')
    def _check_expense_line(self):
        if not len(self.expense_line):
            raise except_orm(_('Warning!'),_('You must add at least one product!'))

    @api.model
    def create(self,val):
        val['name'] = self.env['ir.sequence'].get('product.expense')
        return super(product_expense,self).create(val)


    @api.one
    def unlink(self):
        if self.state != 'draft':
            raise except_orm(_('Warning!'),_("You cannot delete an order whose state is not draft!" ))
        return super(product_expense,self).unlink()

    @api.one
    def copy(self):
         p =  super(product_expense,self).copy()
         p.ref_no=None
         p.expense_line = self.expense_line.copy()
         p.state='draft'
         return p

    def do_ship_end(self):
        self.write({'state':'receive'})
        self.message_post(body=_('shipped the goods,waiting receive'))
        #correcting the account according to the stratgy.
        #1.checking if there's one strategy fit department and product category requirement.
        strategy = self.env['product.expense.account'].search([('department','=',self.staff.department_id.id)])
        account_obj = self.env['account.move']
        account_moves = account_obj.search([('ref','=',self.ref_no.name)])
        #[FIXME] if strategy's catgory is child or parent of current, it should also work.
        if len(strategy):
            for line in self.expense_line:
                res = [s_line for s_line in strategy.line_ids if s_line.product_category==line.product.categ_id]
                if len(res):
                    if len(account_moves):
                        for account_move in account_moves:
                            for a_line in account_move.line_id:
                                if a_line.product_id == line.product and a_line.credit !=0 and a_line.debit==0:
                                    a_line.write({'account_id':res[0].in_account.id})
                                if a_line.product_id == line.product and a_line.debit !=0 and a_line.credit==0:
                                    a_line.write({'account_id':res[0].out_account.id})
    @api.one
    def receive(self):
        self.state = 'done'
        self.message_post(body=_('Received the goods and finished the order!'))

    @api.cr_uid_ids_context
    def view_picking(self,cr,uid,ids,context=None):
        #this function returns an action that display existing picking order.
        mod_obj = self.pool.get('ir.model.data')
        dummy,action_id = tuple(mod_obj.get_object_reference(cr,uid,'stock','action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr,uid,action_id,context=context)
        action['context']={}
        picking = self.browse(cr,uid,ids[0],context=context)
        if picking.ref_no:
            action['domain']="[('id','=',"+str(picking.ref_no.id)+")]"
            action['views']=[(False,"form")]
            action['res_id']=picking.ref_no.id
        return action       
=======
from openerp.exceptions import except_orm

class product_expense(models.Model):
	_name='product.expense'
	
	name = fields.Char('Name',readonly=True)
	staff = fields.Many2one('hr.employee','Employee',required=True)
	department = fields.Many2one('hr.department','Department')
	date = fields.Date('Date')
        expense_line = fields.One2many('product.expense.line','expense_id','Products',states={'draft':[('readonly',False)],'confirm':[('readonly',True)],'accepted':[('readonly',True)],'waiting':[('readonly',True)],'done':[('readonly',True)],'refused':[('readonly',True)]})
	state = fields.Selection(selection=[('draft','Draft'),('confirm','Confirm'),('accepted','Accepted'),('waiting','Waiting'),('done','Done'),('refused','Refused')],string="Status")
	amount = fields.Float('Amount',compute="_get_amount")
	note = fields.Text('Free Notes')
        ref_no = fields.Many2one('stock.picking','Ref Delivery',readonly=True)

	@api.one
	def _get_amount(self):
	    for line in self.expense_line:
		    self.amount += line.subtotal
	
	def action_confirm(self):
		self.state='confirm'

	def action_accept(self):
		self.state='accepted'

	def action_refuse(self):
		self.state='refused'

	def do_transfer(self):
            if self.on_ship_create():
                self.state='waiting'
	

        @api.one
	def on_ship_create(self):
		"""
		Create the delivery order according to product expense order.
		"""
		picking_obj = self.env['stock.picking']
		picking_type_obj = self.env['stock.picking.type']
		picking_type = picking_type_obj.search([('default_location_src_id','=',self.staff.department_id.expense_location.id),('code','=','outgoing')])
		if not picking_type:
                    raise except_orm(_('Warning!'),_("there's no proper location for your department."))

                if not self.ref_no:
                    picking_id = picking_obj.create({
                            "partner_id":self.staff.address_home_id.id,
                            "picking_type_id":picking_type[0].id,
                            "origin":self.name,
                            })

                    self.ref_no = picking_id 

		stock_move_obj = self.env['stock.move']
		stock_quant_obj = self.env['stock.quant']
                expense_loc = self.env['stock.location'].search([('name','=','Expense')])
                if not expense_loc:
                    raise except_orm(_('Warning!'),_("You haven't set expense location"))
		for line in self.expense_line:
			#query per product's stock quant.
			#quants = stock_quant_obj.search([('product_id','=',line.product.id),('location_id.usage','=','internal')])
			#qty=0
		#	for quant in quants:
		#		qty +=quant.qty

		#	if not qty:
                            #if picking_id:
			    #	picking_obj.unlink(picking_id)
                 #           raise except_orm(_('Warning!'),_('Product '+line.product.name+' has not enough quantity.'))

			stock_move_obj.create({
				'picking_id':picking_id.id,
				'product_id':line.product.id,
				'procure_method':'make_to_stock',
				'product_uom_qty':line.quantity,
				'product_uom':line.price_unit.id,
				'name':self.name,
				'location_id':self.staff.department_id.expense_location.id,
				'location_dest_id':expense_loc.id,
				})
                #do transfter
                self.ref_no.action_confirm()
                return True

	@api.one
	@api.constrains('expense_line')
	def _check_expense_line(self):
		if not len(self.expense_line):
                    raise except_orm(_('Warning!'),_('You must add at least one product!'))

        @api.model
        def create(self,val):
            val['name'] = self.env['ir.sequence'].get('product.expense')
            return super(product_expense,self).create(val)

        @api.one
        def unlink(self):
            if self.ref_no:
                raise except_orm(_('Warning!'),_('You must delete the delivery order first!'))
            return super(product_expense,self).unlink()

        @api.onchange('staff')
        def _onchange_staff(self):
            self.department = self.staff.department_id

        @api.one
        def copy(self):
             p =  super(product_expense,self).copy()
             p.ref_no=None
             p.expense_line = self.expense_line.copy()
             p.state='draft'
             return p

        def do_ship_end(self):
            self.write({'state':'done'})
            #correcting the account according to the stratgy.
            #1.checking if there's one strategy fit department and product category requirement.
            strategy = self.env['product.expense.account'].search([('department','=',self.staff.department_id.id)])
            account_obj = self.env['account.move']
            account_moves = account_obj.search([('ref','=',self.ref_no.name)])
            if len(strategy):
                for line in self.expense_line:
                    res = [s_line for s_line in strategy.line_ids if s_line.product_category==line.product.categ_id]
                    if len(res):
                        if len(account_moves):
                            for account_move in account_moves:
                                for a_line in account_move.line_id:
                                    if a_line.product_id == line.product and a_line.credit !=0 and a_line.debit==0:
                                        a_line.write({'account_id':res[0].in_account.id})
                                    if a_line.product_id == line.product and a_line.debit !=0 and a_line.credit==0:
                                        a_line.write({'account_id':res[0].out_account.id})

        #@api.one
        #def test(self):
        #    account_obj = self.env['account.move']
        #    account_moves = account_obj.search([('ref','=',self.ref_no.name)])
        #    print account_moves.line_id
            
>>>>>>> f619c586ca39770e321e0c9d06b854b7bb97e785

            

class product_expense_line(models.Model):
<<<<<<< HEAD

    _name="product.expense.line"

    expense_id = fields.Many2one('product.expense','Expense No')
    department = fields.Many2one('hr.department','Department',related='expense_id.department')
    product = fields.Many2one('product.product','Product',domain=[('hr_expense_ok','=',True)],required=True)
    expense_date = fields.Date('Expense Date')
    comment = fields.Char('Comment')
    price_unit = fields.Many2one('product.uom',string='Unit',related="product.uom_id",readonly=True)
    price = fields.Float('Price',related="product.standard_price")
    quantity = fields.Float('Quantity')
    subtotal = fields.Float(string='Subtotal',compute="_get_total")
    staff = fields.Many2one('hr.employee','Employee',required=True,related="expense_id.staff")
    state = fields.Selection(selection=[('draft','Draft'),('confirm','Confirm'),('accepted','Accepted'),('waiting','Waiting'),('receive','Receive'),('done','Done'),('refused','Refused')],string="Status",related="expense_id.state")

    _defaults={
        'expense_date':datetime.now()
    }

    @api.onchange('product')
    def _check_on_product(self):
        quants = self.env['stock.quant'].search([('location_id','=',self.expense_id.staff.department_id.expense_location.id),('product_id','=',self.product.id)])
        qty = sum([q.qty for q in quants])
        if qty < self.quantity:
            warning = {
                'title': "Warning",
                'message': "Notice : You cannot validate leaves for employee." 
                }                
            return {'warning':warning}
        else:
            return {}

    @api.onchange('product')
    def _onchange_product(self):
        self.price_unit = self.product.uom_id
        self.price = self.product.standard_price        

    @api.one 
    def _get_total(self):
        self.subtotal = self.price*self.quantity

    @api.onchange('quantity')
    def _onchange_quantity(self):
        self.subtotal = self.price * self.quantity
        quants = self.env['stock.quant'].search([('location_id','=',self.expense_id.staff.department_id.expense_location.id),('product_id','=',self.product.id)])
        qty = sum([q.qty for q in quants])
        if qty < self.quantity:
            warning = {
                'title': _("Warning"),
                'message': _("Notice : product ")+self.product.name+_(" quantity is not enough!.Only")+str(qty)+_(" available now!") 
                }                
            return {'warning':warning}
        else:
            return {}

    @api.constrains('quantity')
    def _check_quantity_price(self):
        if self.quantity==0:
            raise except_orm(_('Warning!'),_('The Quantity Can not be Zero!'))


class product_hr_department(models.Model):
    _inherit='hr.department'

    expense_location = fields.Many2one('stock.location','Expense Location',domain=[('usage','=','internal')],required=True)
    strategy = fields.Many2one('product.expense.account','Strategy')
=======
	_name="product.expense.line"
    
        expense_id = fields.Many2one('product.expense','Expense_id')
	product = fields.Many2one('product.product','Product',domain=[('hr_expense_ok','=',True)])
	expense_date = fields.Date('Expense Date')
	comment = fields.Char('Comment')
	price_unit = fields.Many2one('product.uom','Unit')
	price = fields.Float('Price')
	quantity = fields.Float('Quantity')
	subtotal = fields.Float('Subtotal',compute='_get_subtotal')

        @api.onchange('quantity')
        def _onchange_quantity(self):
            self.subtotal = self.price * self.quantity

	@api.one
	def _get_subtotal(self):
	    self.subtotal = self.price * self.quantity

	@api.onchange('product')
	def _onchange_product(self):
		self.price_unit = self.product.uom_id
		self.price = self.product.standard_price

        @api.constrains('quantity','price')
        def _check_quantity_price(self):
            if self.quantity==0 or self.price==0:
                raise except_orm(_('Warning!'),_('The Quantity Or Price Can not be Zero!'))

        @api.multi
        def write(self,val):
            if val.get('price'):
                del val['price']
            return super(product_expense_line,self).write(val)

        @api.model
        def create(self,val):
            val['price'] = self.env['product.product'].browse(val['product']).standard_price
            return super(product_expense_line,self).create(val)

class product_hr_department(models.Model):
	_inherit='hr.department'

	expense_location = fields.Many2one('stock.location','Expense Location',domain=[('usage','=','internal')],required=True)
        strategy = fields.Many2one('product.expense.account','Strategy')
>>>>>>> f619c586ca39770e321e0c9d06b854b7bb97e785

class product_expense_picking(models.Model):
    _inherit='stock.picking'

    @api.one
    def do_transfer(self):
        res =  super(product_expense_picking,self).do_transfer()
        if res:
            expense = self.env['product.expense'].search([('ref_no','=',self.id)])
            if expense:
                workflow.trg_validate(self.env.user.id,'product.expense',expense.id,'ship_end',self.env.cr)
<<<<<<< HEAD
        return res 
=======
        return res 
>>>>>>> f619c586ca39770e321e0c9d06b854b7bb97e785
