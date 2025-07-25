from fastapi import APIRouter, HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from typing import Any, Dict, List
from ..core.db import department_collection, employee_collection, benefit_collection
from ..logs.logger import logger
from app.models.Department import DepartmentOut, DepartmentCreate, PaginatedDepartmentResponse

router = APIRouter(prefix="/departments", tags=["Departments"])

@router.post("/", response_model=DepartmentOut)
async def create_department(department: DepartmentCreate):
    logger.debug(f"Tentando criar departamento: {department}")
    try:
        department_dict = department.model_dump(exclude_unset=True)
        result = await department_collection.insert_one(department_dict)
        created = await department_collection.find_one({"_id": result.inserted_id})
        if created:
            created["_id"] = str(created["_id"])
            logger.info(f"Departamento criado com sucesso: {created}")
            return created
        raise HTTPException(status_code=500, detail="Erro ao criar departamento")
    except Exception as e:
        logger.exception(f"Erro ao criar departamento: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno ao criar departamento")

@router.get("/", response_model=PaginatedDepartmentResponse)
async def list_departments(skip: int = 0, limit: int = 10):
    logger.debug(f"Listando departamentos com skip={skip}, limit={limit}")
    try:
        total = await department_collection.count_documents({})
        departments = await department_collection.find().skip(skip).limit(limit).to_list(length=limit)
        for dep in departments:
            dep["_id"] = str(dep["_id"])
        logger.info(f"{len(departments)} departamentos encontrados")
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": departments
        }
    except Exception:
        logger.exception("Erro ao listar departamentos")
        raise HTTPException(status_code=500, detail="Erro interno ao listar departamentos")
    
@router.get("/count")
async def count_departments():
    try:
        count = await department_collection.count_documents({})
        logger.info(f"Total de departamentos: {count}")
        return {"count": count}
    except Exception:
        logger.exception("Erro ao contar departamentos")
        raise HTTPException(status_code=500, detail="Erro interno ao contar departamentos")

@router.put("/{department_id}", response_model=DepartmentOut)
async def update_department(department_id: str, update_data: DepartmentCreate):
    logger.debug(f"Atualizando departamento ID {department_id} com dados {update_data}")
    try:
        oid = ObjectId(department_id)
        update = update_data.model_dump(exclude_unset=True)
        result = await department_collection.update_one({"_id": oid}, {"$set": update})
        if result.matched_count == 0:
            logger.warning(f"Departamento ID {department_id} não encontrado para atualização")
            raise HTTPException(status_code=404, detail="Departamento não encontrado")
        updated = await department_collection.find_one({"_id": oid})
        updated["_id"] = str(updated["_id"])
        logger.info(f"Departamento ID {department_id} atualizado com sucesso")
        return updated
    except InvalidId:
        logger.warning(f"ID inválido: {department_id}")
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception:
        logger.exception(f"Erro ao atualizar departamento ID {department_id}")
        raise HTTPException(status_code=500, detail="Erro interno ao atualizar departamento")

@router.delete("/{department_id}")
async def delete_department(department_id: str):
    logger.debug(f"Tentando deletar departamento ID {department_id}")
    try:
        oid = ObjectId(department_id)

        # 1. Atualiza os funcionários, removendo o departamento deles
        result_update = await employee_collection.update_many(
            {"department_id": department_id},
            {"$set": {"department_id": None}}
        )
        logger.info(f"{result_update.modified_count} funcionários tiveram o campo department_id removido")

        # 2. Deleta o departamento
        result_delete = await department_collection.delete_one({"_id": oid})
        if result_delete.deleted_count == 0:
            logger.warning(f"Departamento ID {department_id} não encontrado para deleção")
            raise HTTPException(status_code=404, detail="Departamento não encontrado")

        logger.info(f"Departamento ID {department_id} deletado com sucesso")
        return {
            "detail": "Departamento deletado com sucesso",
            "employees_updated": result_update.modified_count
        }

    except InvalidId:
        logger.warning(f"ID inválido: {department_id}")
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception:
        logger.exception(f"Erro ao deletar departamento ID {department_id}")
        raise HTTPException(status_code=500, detail="Erro interno ao deletar departamento")

@router.get("/get_by_name", response_model=List[DepartmentOut])
async def get_departments_by_name(name: str, skip: int = 0, limit: int = 10):
    logger.debug(f"Buscando departamentos com nome contendo '{name}'")
    try:
        departments = await department_collection.find(
            {"name": {"$regex": name, "$options": "i"}}
        ).skip(skip).limit(limit).to_list(length=limit)
        for dep in departments:
            dep["_id"] = str(dep["_id"])
        logger.info(f"{len(departments)} departamentos encontrados com nome '{name}'")
        return departments
    except Exception:
        logger.exception("Erro ao buscar departamentos por nome")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar departamentos por nome")
    
@router.get("/get_department_by_manager", response_model=List[DepartmentOut])
async def get_departments_by_manager(manager_id: str):
    logger.debug(f"Buscando departamentos com gerente ID {manager_id}")
    try:
        # Remover a conversão para ObjectId
        departments = await department_collection.find({"manager_id": manager_id}).to_list(length=None)
        for dep in departments:
            dep["_id"] = str(dep["_id"])
        logger.info(f"{len(departments)} departamentos encontrados com gerente ID {manager_id}")
        return departments
    except Exception:
        logger.exception(f"Erro ao buscar departamentos por gerente {manager_id}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar departamentos por gerente")

@router.get("/get_by_employee/{employee_id}", response_model=List[DepartmentOut])
async def get_departments_by_employee(employee_id: str):
    logger.debug(f"Buscando departamentos com funcionário ID {employee_id}")
    try:
        departments = await department_collection.find({"employee_ids": employee_id}).to_list(length=None)
        for dep in departments:
            dep["_id"] = str(dep["_id"])
        logger.info(f"{len(departments)} departamentos encontrados com funcionário ID {employee_id}")
        return departments
    except Exception:
        logger.exception(f"Erro ao buscar departamentos por funcionário {employee_id}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar departamentos por funcionário")
    
@router.get("/departments/full_info", response_model=List[Dict[str, Any]])
async def get_departments_with_employees_and_benefits():
    try:
        departments = await department_collection.find().to_list(length=None)
        full_info = []

        for dep in departments:
            dep_id = str(dep["_id"])
            employees = await employee_collection.find({"department_id": dep_id}).to_list(length=None)
            
            enriched_employees = []
            for emp in employees:
                benefit_ids = [ObjectId(bid) for bid in emp.get("benefits_id", [])]
                benefits = await benefit_collection.find({"_id": {"$in": benefit_ids}}).to_list(length=None)
                for b in benefits:
                    b["_id"] = str(b["_id"])
                emp["_id"] = str(emp["_id"])
                emp["benefits"] = benefits
                enriched_employees.append(emp)

            full_info.append({
                "department_id": dep_id,
                "department_name": dep["name"],
                "location": dep.get("location"),
                "employees": enriched_employees
            })

        return full_info
    except Exception as e:
        logger.exception(f"Erro ao buscar estrutura completa dos departamentos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar dados completos")

    
@router.get("/{department_id}", response_model=DepartmentOut)
async def get_department(department_id: str):
    logger.debug(f"Buscando departamento com ID {department_id}")
    try:
        oid = ObjectId(department_id)
        department = await department_collection.find_one({"_id": oid})
        if not department:
            logger.warning(f"Departamento ID {department_id} não encontrado")
            raise HTTPException(status_code=404, detail="Departamento não encontrado")
        department["_id"] = str(department["_id"])
        return department
    except InvalidId:
        logger.warning(f"ID inválido: {department_id}")
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception:
        logger.exception(f"Erro ao buscar departamento ID {department_id}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar departamento")
